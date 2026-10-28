"""Import WP brands, reviews and industries into the main app.

Every row is keyed on its WP id (term_id, post ID, or the deterministic reviewer uuid), so a
re-run updates in place: changed rows are written, unchanged rows are left alone, and a slug
is just another attribute. Postgres mirrors the import set: a row that was imported before but
is now unpublished, trashed, deleted or invalid in WP is deleted here.
"""

from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from shared_auth import deterministic_uuid

from .mirror import mirror
from .models import Brand, Industry, Review, Reviewer
from .wp_source import WPPost, WPSource, WPUser

PUBLISHED = "publish"
# Model -> its name in the import report, in import order.
TABLES = {Industry: "industries", Reviewer: "reviewers", Brand: "brands", Review: "reviews"}


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


def brand_fields(post: WPPost, industry_pk: dict[int, int]) -> dict | None:
    """Brand field values for a WP brand post, or None if it is not imported."""
    if post.status != PUBLISHED:
        return None
    industry_ids = [industry_pk[t] for t in post.term_ids if t in industry_pk]
    return {
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


def review_fields(post: WPPost, brand_pk: dict[int, int], users: dict[int, WPUser]) -> dict | None:
    """Review field values for a WP review post, or None if it is unpublished, has no
    imported brand or has a rating outside 1-5."""
    brand_id = brand_pk.get(_int(post.meta.get("brand")))
    rating = _int(post.meta.get("rating"))
    if post.status != PUBLISHED or brand_id is None or rating not in range(1, 6):
        return None
    return {
        "brand_id": brand_id,
        "reviewer_id": deterministic_uuid("wp_user", post.author) if post.author in users else None,
        "title": post.title,
        "slug": post.slug,
        "body": post.content,
        "rating": rating,
        "reviewer_location": post.meta.get("reviewer_location", ""),
        "published_at": _aware(post.date),
        "modified_at": _aware(post.modified),
    }


@transaction.atomic
def import_source(src: WPSource) -> dict[str, Counter]:
    counts = defaultdict(Counter)

    industries = {t.id: {"name": t.name, "slug": t.slug} for t in src.industries}
    mirror(Industry, "wp_id", industries, counts)
    industry_pk = dict(Industry.objects.values_list("wp_id", "pk"))

    brands = {post.id: brand_fields(post, industry_pk) for post in src.brands}
    counts[Brand]["skipped"] += sum(fields is None for fields in brands.values())
    mirror(Brand, "wp_id", {k: v for k, v in brands.items() if v}, counts)
    brand_pk = dict(Brand.objects.values_list("wp_id", "pk"))

    users = {u.id: u for u in src.users}
    reviews = {post.id: review_fields(post, brand_pk, users) for post in src.reviews}
    counts[Review]["skipped"] += sum(fields is None for fields in reviews.values())
    reviews = {k: v for k, v in reviews.items() if v}
    authors = {post.author for post in src.reviews if post.id in reviews and post.author in users}
    reviewers = {
        deterministic_uuid("wp_user", author): {"display_name": users[author].display_name}
        for author in authors
    }
    mirror(Reviewer, "id", reviewers, counts)
    mirror(Review, "wp_id", reviews, counts)

    return {name: counts[model] for model, name in TABLES.items()}
