"""Import WP brands, reviews and industries (R2). The WP database is only read.

Every row is keyed on its WP id (term_id, post ID, or the deterministic reviewer uuid), so a
re-run updates in place: changed rows are written, unchanged rows are left alone, and a slug
is just another attribute. Postgres mirrors the import set: a row that was imported before but
is now unpublished, trashed, deleted or invalid in WP is deleted here.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import pymysql
from cauth import deterministic_uuid
from django.conf import settings
from django.db import transaction

from .models import Brand, Industry, Review, Reviewer

PUBLISHED = "publish"
TABLES = {Industry: "industries", Reviewer: "reviewers", Brand: "brands", Review: "reviews"}


@dataclass(frozen=True)
class WPTerm:
    id: int
    name: str
    slug: str


@dataclass(frozen=True)
class WPUser:
    id: int
    display_name: str


@dataclass(frozen=True)
class WPPost:
    id: int
    slug: str
    title: str
    content: str
    excerpt: str
    status: str
    date: datetime  # UTC, naive as stored by WP
    modified: datetime
    author: int
    meta: dict[str, str] = field(default_factory=dict)
    term_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class WPSource:
    industries: list[WPTerm]
    users: list[WPUser]
    brands: list[WPPost]
    reviews: list[WPPost]


def fetch_source() -> WPSource:
    p = settings.WP_TABLE_PREFIX
    conn = pymysql.connect(**settings.WP_DB, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            # One read-only snapshot: the import can never write to WP, and brands,
            # reviews and meta are read as of the same moment.
            cur.execute("START TRANSACTION READ ONLY")
            cur.execute(
                f"SELECT t.term_id, t.name, t.slug FROM {p}terms t"
                f" JOIN {p}term_taxonomy tt ON tt.term_id = t.term_id"
                f" WHERE tt.taxonomy = 'industry' ORDER BY t.term_id"
            )
            industries = [WPTerm(*row) for row in cur.fetchall()]
            cur.execute(f"SELECT ID, display_name FROM {p}users ORDER BY ID")
            users = [WPUser(*row) for row in cur.fetchall()]
            cur.execute(
                f"SELECT ID, post_type, post_name, post_title, post_content, post_excerpt,"
                f" post_status,"
                f" IF(post_date_gmt = '0000-00-00 00:00:00', post_date, post_date_gmt),"
                f" IF(post_modified_gmt = '0000-00-00 00:00:00', post_modified, post_modified_gmt),"
                f" post_author"
                f" FROM {p}posts WHERE post_type IN ('brand', 'review') ORDER BY ID"
            )
            posts = cur.fetchall()
            cur.execute(
                f"SELECT m.post_id, m.meta_key, m.meta_value FROM {p}postmeta m"
                f" JOIN {p}posts po ON po.ID = m.post_id"
                f" WHERE po.post_type IN ('brand', 'review')"
            )
            meta = defaultdict(dict)
            for post_id, key, value in cur.fetchall():
                meta[post_id][key] = value or ""
            cur.execute(
                f"SELECT tr.object_id, tt.term_id FROM {p}term_relationships tr"
                f" JOIN {p}term_taxonomy tt ON tt.term_taxonomy_id = tr.term_taxonomy_id"
                f" WHERE tt.taxonomy = 'industry' ORDER BY tt.term_id"
            )
            terms = defaultdict(list)
            for object_id, term_id in cur.fetchall():
                terms[object_id].append(term_id)
            cur.execute("COMMIT")
    finally:
        conn.close()

    by_type = defaultdict(list)
    for post_id, post_type, *rest in posts:
        by_type[post_type].append(
            WPPost(post_id, *rest, meta=meta[post_id], term_ids=tuple(terms[post_id]))
        )
    return WPSource(industries, users, by_type["brand"], by_type["review"])


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC)


def _int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _rating(value: str | None) -> Decimal | None:
    """An ACF average on the 0-5 review scale, or None (it must fit numeric(2,1))."""
    try:
        rating = Decimal(str(value).strip()).quantize(Decimal("0.1"))
        return rating if 0 <= rating <= 5 else None
    except (InvalidOperation, ValueError):  # comparing NaN raises InvalidOperation
        return None


def _sync(model, key_field: str, rows: dict, all_counts: dict[str, Counter]) -> None:
    """Upsert rows ({key: field values}), delete rows not among them, and count
    created/updated/unchanged/deleted (cascaded deletes count against their own table)."""
    # Deleting first also frees the slugs of rows that left the import set.
    _, deleted = model.objects.exclude(**{f"{key_field}__in": list(rows)}).delete()
    for other, name in TABLES.items():
        all_counts[name]["deleted"] += deleted.get(other._meta.label, 0)
    counts = all_counts[TABLES[model]]
    existing = model.objects.in_bulk(list(rows), field_name=key_field)
    # Park slugs that are about to change, so a rename into a slug another row only
    # gives up later in the loop (or a swap) cannot hit the unique index.
    if any(f.name == "slug" for f in model._meta.fields):
        for key, obj in existing.items():
            if obj.slug != rows[key]["slug"]:
                model.objects.filter(pk=obj.pk).update(slug=f"wp-import-parked-{obj.pk}")
                obj.slug = None
    for key, values in rows.items():
        obj = existing.get(key)
        if obj is None:
            model.objects.create(**{key_field: key}, **values)
            counts["created"] += 1
            continue
        changed = [name for name, value in values.items() if getattr(obj, name) != value]
        if changed:
            for name in changed:
                setattr(obj, name, values[name])
            obj.save(update_fields=changed)
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1


@transaction.atomic
def import_source(src: WPSource) -> dict[str, Counter]:
    counts = {name: Counter() for name in TABLES.values()}

    _sync(
        Industry,
        "wp_id",
        {t.id: {"name": t.name, "slug": t.slug} for t in src.industries},
        counts,
    )
    industry_pk = dict(Industry.objects.values_list("wp_id", "pk"))

    brand_rows = {}
    for post in src.brands:
        if post.status != PUBLISHED:
            counts["brands"]["skipped"] += 1
            continue
        industry_ids = [industry_pk[t] for t in post.term_ids if t in industry_pk]
        brand_rows[post.id] = {
            "name": post.title,
            "slug": post.slug,
            "description": post.content,
            "excerpt": post.excerpt,
            # One industry per brand: WP allows several terms, the lowest term id wins.
            "industry_id": industry_ids[0] if industry_ids else None,
            "website_url": post.meta.get("website_url", ""),
            "founded_year": _int(post.meta.get("founded_year")),
            "headquarters": post.meta.get("headquarters", ""),
            "legacy_average_rating": _rating(post.meta.get("average_rating")),
            "seo_title": post.meta.get("_yoast_wpseo_title", ""),
            "seo_description": post.meta.get("_yoast_wpseo_metadesc", ""),
            "published_at": _aware(post.date),
            "modified_at": _aware(post.modified),
        }
    _sync(Brand, "wp_id", brand_rows, counts)
    brand_pk = dict(Brand.objects.values_list("wp_id", "pk"))

    users = {u.id: u for u in src.users}
    reviewer_rows, review_rows = {}, {}
    for post in src.reviews:
        brand_id = brand_pk.get(_int(post.meta.get("brand")))
        rating = _int(post.meta.get("rating"))
        if post.status != PUBLISHED or brand_id is None or rating not in range(1, 6):
            counts["reviews"]["skipped"] += 1
            continue
        reviewer_id = None
        if post.author in users:
            reviewer_id = deterministic_uuid("wp_user", post.author)
            reviewer_rows[reviewer_id] = {"display_name": users[post.author].display_name}
        review_rows[post.id] = {
            "brand_id": brand_id,
            "reviewer_id": reviewer_id,
            "title": post.title,
            "slug": post.slug,
            "body": post.content,
            "rating": rating,
            "reviewer_location": post.meta.get("reviewer_location", ""),
            "published_at": _aware(post.date),
            "modified_at": _aware(post.modified),
        }
    _sync(Reviewer, "id", reviewer_rows, counts)
    _sync(Review, "wp_id", review_rows, counts)
    return counts
