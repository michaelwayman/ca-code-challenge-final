from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from django.db import connection
from django.test import SimpleTestCase, TestCase

from .models import Brand, Industry, Review, Reviewer
from .wp_import import WPPost, WPSource, WPTerm, WPUser, import_source, map_source, wp_user_uuid

T0 = datetime(2026, 5, 19, 20, 29, 2)


def brand(id, slug, status="publish", meta=None, term_ids=(2,)):
    if meta is None:
        meta = {
            "website_url": f"https://{slug}.example.com",
            "founded_year": "1985",
            "headquarters": "Hartford, CT",
            "average_rating": "4.2",
            "_website_url": "field_brand_website_url",
            "_yoast_wpseo_title": f"{slug} reviews",
            "_yoast_wpseo_metadesc": f"Read reviews of {slug}",
        }
    return WPPost(id, slug, slug.title(), "<p>Body</p>", "", status, T0, T0, 0, meta, term_ids)


def review(id, slug, brand_id, rating="5", author=2, status="publish"):
    meta = {"brand": str(brand_id), "rating": rating, "reviewer_location": "Denver, CO"}
    return WPPost(id, slug, slug.title(), "<p>Great</p>", "", status, T0, T0, author, meta)


def source(**overrides):
    fields = {
        "industries": [WPTerm(2, "Insurance", "insurance"), WPTerm(3, "Telecom", "telecom")],
        "users": [WPUser(1, "admin"), WPUser(2, "Sarah K.")],
        "brands": [brand(7, "acme-insurance"), brand(8, "primepath-bank", term_ids=(3,))],
        "reviews": [review(12, "smooth-claim", 7), review(13, "pricey", 7, rating="3")],
    }
    fields.update(overrides)
    return WPSource(**fields)


def row_counts():
    return {m.__name__: m.objects.count() for m in (Industry, Reviewer, Brand, Review)}


class SchemaTests(TestCase):
    def test_no_key_value_meta_table(self):
        tables = connection.introspection.table_names()
        self.assertFalse([t for t in tables if "meta" in t], tables)

    def test_average_rating_is_derived_not_stored(self):
        columns = {f.column for f in Brand._meta.concrete_fields}
        self.assertNotIn("average_rating", columns)
        self.assertIn("legacy_average_rating", columns)
        import_source(source())
        acme = Brand.objects.with_stats().get(slug="acme-insurance")
        self.assertEqual(acme.average_rating, 4)
        self.assertEqual(acme.review_count, 2)
        self.assertEqual(acme.legacy_average_rating, Decimal("4.2"))


class MappingTests(SimpleTestCase):
    """map_source is pure: these run with no database."""

    def test_maps_published_rows_keyed_on_wp_id(self):
        m = map_source(source())
        self.assertEqual(set(m.brands), {7, 8})
        self.assertEqual(m.brands[7]["industry_wp_id"], 2)
        self.assertEqual(m.brands[7]["founded_year"], 1985)
        self.assertEqual(m.reviews[13]["brand_wp_id"], 7)
        self.assertEqual(m.reviews[13]["reviewer_id"], wp_user_uuid(2))
        self.assertEqual(list(m.reviewers), [wp_user_uuid(2)])

    def test_skips_drafts_missing_brand_and_bad_ratings(self):
        m = map_source(
            source(
                brands=[brand(7, "acme-insurance"), brand(9, "draft-co", status="draft")],
                reviews=[
                    review(12, "ok", 7),
                    review(13, "no-brand", 99),
                    review(14, "bad-rating", 7, rating="6"),
                    review(15, "draft-brand", 9),
                ],
            )
        )
        self.assertEqual(set(m.reviews), {12})
        self.assertEqual(m.skipped["brands"], 1)
        self.assertEqual(m.skipped["reviews"], 3)

    def test_out_of_range_average_rating_is_null(self):
        meta = {"average_rating": "7"}
        m = map_source(source(brands=[brand(7, "acme-insurance", meta=meta)], reviews=[]))
        self.assertIsNone(m.brands[7]["legacy_average_rating"])


class ImportTests(TestCase):
    def test_first_run_creates_typed_rows(self):
        counts = import_source(source())
        self.assertEqual(counts["brands"]["created"], 2)
        self.assertEqual(counts["reviews"]["created"], 2)
        self.assertEqual(counts["industries"]["created"], 2)
        acme = Brand.objects.get(wp_id=7)
        self.assertEqual(acme.industry.slug, "insurance")
        self.assertEqual(acme.founded_year, 1985)
        self.assertEqual(acme.seo_title, "acme-insurance reviews")
        self.assertEqual(Review.objects.get(wp_id=13).rating, 3)

    def test_rerun_leaves_counts_identical_and_reports_unchanged(self):
        import_source(source())
        before = row_counts()
        counts = import_source(source())
        self.assertEqual(row_counts(), before)
        for name in ("industries", "reviewers", "brands", "reviews"):
            self.assertEqual(counts[name]["created"], 0, name)
            self.assertEqual(counts[name]["updated"], 0, name)

    def test_changed_slug_updates_row_not_duplicates(self):
        import_source(source())
        before = row_counts()
        src = source()
        renamed = replace(
            src, brands=[replace(src.brands[0], slug="acme-insurance-co"), src.brands[1]]
        )
        counts = import_source(renamed)
        self.assertEqual(row_counts(), before)
        self.assertEqual(counts["brands"]["updated"], 1)
        self.assertEqual(Brand.objects.get(wp_id=7).slug, "acme-insurance-co")
        self.assertFalse(Brand.objects.filter(slug="acme-insurance").exists())

    def test_slug_swap_does_not_hit_unique_index(self):
        import_source(source())
        swapped = source(brands=[brand(7, "primepath-bank"), brand(8, "acme-insurance")])
        import_source(swapped)
        self.assertEqual(Brand.objects.get(wp_id=7).slug, "primepath-bank")
        self.assertEqual(Brand.objects.get(wp_id=8).slug, "acme-insurance")

    def test_field_edit_in_wp_reflected_on_rerun(self):
        import_source(source())
        edited = source(
            reviews=[review(12, "smooth-claim", 7, rating="1"), review(13, "pricey", 7)]
        )
        import_source(edited)
        self.assertEqual(Review.objects.get(wp_id=12).rating, 1)

    def test_unpublished_and_orphan_rows_skipped(self):
        src = source(
            brands=[brand(7, "acme-insurance"), brand(9, "draft-brand", status="draft")],
            reviews=[
                review(12, "ok", 7),
                review(14, "draft", 7, status="draft"),
                review(15, "no-brand", 99),
                review(16, "bad-rating", 7, rating="9"),
            ],
        )
        counts = import_source(src)
        self.assertEqual(counts["brands"]["skipped"], 1)
        self.assertEqual(counts["reviews"]["skipped"], 3)
        self.assertEqual(list(Review.objects.values_list("wp_id", flat=True)), [12])

    def test_rows_leaving_the_import_set_are_deleted_on_rerun(self):
        import_source(source())
        src = source(
            users=[WPUser(1, "admin"), WPUser(2, "Sarah K."), WPUser(3, "Lee")],
            brands=[brand(7, "acme-insurance"), brand(8, "primepath-bank", status="trash")],
            reviews=[
                review(12, "smooth-claim", 7, status="draft"),
                review(13, "pricey", 7, rating="9"),
                review(17, "fresh", 7, author=3),
            ],
        )
        counts = import_source(src)
        self.assertEqual(counts["brands"]["deleted"], 1)
        self.assertEqual(counts["reviews"]["deleted"], 2)
        self.assertEqual(counts["reviewers"]["deleted"], 1)
        self.assertEqual(list(Brand.objects.values_list("wp_id", flat=True)), [7])
        self.assertEqual(list(Review.objects.values_list("wp_id", flat=True)), [17])
        self.assertEqual(list(Reviewer.objects.values_list("pk", flat=True)), [wp_user_uuid(3)])
        # Publishing again brings the rows back.
        counts = import_source(source())
        self.assertEqual(counts["brands"]["created"], 1)
        self.assertEqual(Review.objects.filter(wp_id__in=[12, 13]).count(), 2)

    def test_new_post_can_take_the_slug_of_a_row_that_left_the_import_set(self):
        import_source(source())
        src = source(
            brands=[brand(7, "acme-insurance", status="trash"), brand(11, "acme-insurance")],
            reviews=[review(12, "smooth-claim", 11)],
        )
        counts = import_source(src)
        # Trashing brand 7 cascades to both its reviews; 12 comes back under brand 11.
        self.assertEqual(counts["reviews"]["deleted"], 2)
        self.assertEqual(counts["reviews"]["created"], 1)
        self.assertEqual(Brand.objects.get(slug="acme-insurance").wp_id, 11)
        self.assertFalse(Brand.objects.filter(wp_id=7).exists())
        self.assertEqual(Review.objects.get(wp_id=12).brand.wp_id, 11)

    def test_out_of_range_legacy_average_rating_becomes_null(self):
        for value in ("10", "99.5", "-1", "5.1", "NaN", "Infinity"):
            meta = {"average_rating": value}
            import_source(source(brands=[brand(7, "acme-insurance", meta=meta)], reviews=[]))
            self.assertIsNone(Brand.objects.get(wp_id=7).legacy_average_rating, value)
        import_source(source(brands=[brand(7, "acme-insurance", meta={"average_rating": "5"})]))
        self.assertEqual(Brand.objects.get(wp_id=7).legacy_average_rating, Decimal("5.0"))

    def test_wp_user_uuid_is_pinned(self):
        # The same two values are pinned in the other service's tests: the rule must not drift.
        self.assertEqual(str(wp_user_uuid(1)), "6b9b9787-70dc-5a6d-82ce-13817d92b721")
        self.assertEqual(str(wp_user_uuid(2)), "2723c39b-b3ba-5ff4-886d-340042c07697")

    def test_reviewer_keyed_by_wp_user_uuid_without_wp_id(self):
        import_source(source())
        reviewer = Review.objects.get(wp_id=12).reviewer
        self.assertEqual(reviewer.pk, wp_user_uuid(2))
        self.assertEqual(reviewer.display_name, "Sarah K.")
        self.assertEqual([f.name for f in Reviewer._meta.concrete_fields], ["id", "display_name"])
        # Only authors of imported reviews become reviewers, not every WP user.
        self.assertEqual(Reviewer.objects.count(), 1)

    def test_blank_acf_values_become_nulls(self):
        blank = brand(7, "acme-insurance", meta={"founded_year": "", "average_rating": ""})
        import_source(source(brands=[blank]))
        acme = Brand.objects.get(wp_id=7)
        self.assertIsNone(acme.founded_year)
        self.assertIsNone(acme.legacy_average_rating)
        self.assertEqual(acme.website_url, "")
