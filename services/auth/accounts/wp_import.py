"""Import wp_users into auth users (R10). The WP database is only read."""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import pymysql
from cauth import Role
from django.conf import settings
from django.db import transaction

from .models import User

# WP user id -> UUID. The auth service uses it as the user's pk and the main app as the reviewer's
# pk, so the two link with no runtime call (A3). The rule is the contract
# docs/contracts/auth/reviewer-ids.json; a test in each service checks it.
WP_USER_NAMESPACE = uuid.UUID("b88cc69f-2c32-5407-a15f-e0e254c8057a")


def wp_user_uuid(wp_user_id: int) -> uuid.UUID:
    return uuid.uuid5(WP_USER_NAMESPACE, str(wp_user_id))


EDITOR_WP_ROLES = {"administrator", "editor"}
_CAPABILITY = re.compile(r's:\d+:"([^"]+)";b:1;')


@dataclass(frozen=True)
class WPUser:
    id: int
    login: str
    email: str
    password_hash: str
    registered: datetime
    capabilities: str  # PHP-serialized {prefix}capabilities usermeta, "" if absent


def map_role(capabilities: str) -> Role:
    """administrator/editor become editor, every other WP role becomes reader."""
    wp_roles = set(_CAPABILITY.findall(capabilities or ""))
    return Role.EDITOR if wp_roles & EDITOR_WP_ROLES else Role.READER


def fetch_wp_users() -> list[WPUser]:
    prefix = settings.WP_TABLE_PREFIX
    conn = pymysql.connect(**settings.WP_DB, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT u.ID, u.user_login, u.user_email, u.user_pass, u.user_registered,"
                f" COALESCE(m.meta_value, '')"
                f" FROM {prefix}users u"
                f" LEFT JOIN {prefix}usermeta m"
                f"  ON m.user_id = u.ID AND m.meta_key = %s"
                f" ORDER BY u.ID",
                [f"{prefix}capabilities"],
            )
            return [WPUser(*row) for row in cur.fetchall()]
    finally:
        conn.close()


@transaction.atomic
def import_users(wp_users: list[WPUser]) -> dict[str, int]:
    """Upsert by the pk that wp_user_uuid derives. Password and role are set on create only: after
    that the auth service owns them (R13), so a re-run never reverts a rehash."""
    counts = {"created": 0, "updated": 0}
    by_pk = {wp_user_uuid(wp.id): wp for wp in wp_users}
    # Park every username that is about to change, so a WP rename into a login another
    # imported user only gives up later in the loop (or a swap) cannot hit the unique index.
    for pk, username in User.objects.filter(pk__in=by_pk).values_list("pk", "username"):
        if username != by_pk[pk].login:
            User.objects.filter(pk=pk).update(username=f"wp-import-{pk.hex}")
    for pk, wp in by_pk.items():
        _, created = User.objects.update_or_create(
            pk=pk,
            defaults={"username": wp.login, "email": wp.email},
            create_defaults={
                "username": wp.login,
                "email": wp.email,
                "password": wp.password_hash,
                "role": map_role(wp.capabilities),
                # user_registered is stored in UTC without a zone.
                "date_joined": wp.registered.replace(tzinfo=UTC),
            },
        )
        counts["created" if created else "updated"] += 1
    return counts
