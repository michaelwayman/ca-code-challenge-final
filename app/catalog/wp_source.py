"""Read brands, reviews, industries and users from the WordPress database, read-only and as
one consistent snapshot. Nothing here knows about the main app's models."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import pymysql
from django.conf import settings


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
