from datetime import UTC, datetime, timedelta
from itertools import count

from django.test import TestCase

from .models import Brand, Industry, Review, Reviewer

T0 = datetime(2026, 5, 19, tzinfo=UTC)
ids = count(1)
URL = "/api/brands/"


def make_brand(slug, industry=None, **fields):
    fields.setdefault("published_at", T0)
    fields.setdefault("modified_at", T0)
    return Brand.objects.create(
        wp_id=next(ids), name=slug.replace("-", " ").title(), slug=slug, industry=industry, **fields
    )


def make_review(brand, rating, days=0, reviewer=None, **fields):
    n = next(ids)
    fields.setdefault("body", "<p>Solid <b>service</b></p>")
    return Review.objects.create(
        wp_id=n,
        brand=brand,
        reviewer=reviewer,
        title=f"Review {n}",
        slug=f"review-{n}",
        rating=rating,
        published_at=T0 + timedelta(days=days),
        modified_at=T0,
        **fields,
    )


class BrandListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.insurance = Industry.objects.create(wp_id=1, name="Insurance", slug="insurance")
        cls.telecom = Industry.objects.create(wp_id=2, name="Telecom", slug="telecom")
        cls.banking = Industry.objects.create(wp_id=3, name="Banking", slug="banking")
        cls.sarah = Reviewer.objects.create(
            id="00000000-0000-0000-0000-000000000002", display_name="Sarah K."
        )
        cls.acme = make_brand(
            "acme-insurance", cls.insurance, excerpt="Cheap cover.", description="<p>Long</p>"
        )
        cls.zephyr = make_brand("zephyr-mobile", cls.telecom, description="<p>Fast <i>5G</i></p>")
        cls.bolt = make_brand("bolt-bank", cls.banking)
        make_review(cls.acme, 5, reviewer=cls.sarah)
        make_review(cls.acme, 3)
        for rating in (4, 4, 4):
            make_review(cls.zephyr, rating)
        # bolt-bank has no reviews.

    def get(self, **params):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def slugs(self, **params):
        return [row["slug"] for row in self.get(**params)["results"]]

    def test_envelope_and_row_shape(self):
        body = self.get()
        self.assertEqual(set(body), {"count", "next", "previous", "results"})
        self.assertEqual(body["count"], 3)
        acme = body["results"][0]
        self.assertEqual(
            set(acme),
            {
                "name",
                "slug",
                "industry",
                "average_rating",
                "review_count",
                "short_description",
                "top_review",
            },
        )
        self.assertEqual(acme["industry"], {"name": "Insurance", "slug": "insurance"})
        self.assertEqual(acme["average_rating"], 4.0)
        self.assertEqual(acme["review_count"], 2)
        self.assertEqual(acme["short_description"], "Cheap cover.")
        self.assertEqual(acme["top_review"]["rating"], 5)
        self.assertEqual(acme["top_review"]["reviewer"], "Sarah K.")
        self.assertEqual(acme["top_review"]["snippet"], "Solid service")

    def test_short_description_falls_back_to_stripped_body(self):
        zephyr = next(r for r in self.get()["results"] if r["slug"] == "zephyr-mobile")
        self.assertEqual(zephyr["short_description"], "Fast 5G")

    def test_snippets_decode_html_entities(self):
        brand = make_brand("fish-shop", description="<p>Fish &amp; chips &#8211; it&#8217;s</p>")
        make_review(brand, 4, body="<p>Tom &amp; Jerry&#8217;s at AT&T</p>")
        row = next(r for r in self.get()["results"] if r["slug"] == "fish-shop")
        self.assertEqual(row["short_description"], "Fish & chips – it’s")
        self.assertEqual(row["top_review"]["snippet"], "Tom & Jerry’s at AT&T")

    def test_unauthenticated_call_succeeds(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_listing_is_publicly_cacheable(self):
        response = self.client.get(URL)
        self.assertEqual(
            response["Cache-Control"], "public, max-age=30, stale-while-revalidate=120"
        )

    def test_industry_filter_is_repeatable(self):
        self.assertEqual(self.slugs(industry="telecom"), ["zephyr-mobile"])
        self.assertEqual(
            self.slugs(industry=["telecom", "insurance"]), ["acme-insurance", "zephyr-mobile"]
        )
        self.assertEqual(self.slugs(industry="nope"), [])
        all_brands = ["acme-insurance", "bolt-bank", "zephyr-mobile"]
        self.assertEqual(self.slugs(industry=""), all_brands)
        self.assertEqual(self.slugs(industry=["", "telecom"]), ["zephyr-mobile"])

    def test_ordering(self):
        by_name = ["acme-insurance", "bolt-bank", "zephyr-mobile"]
        self.assertEqual(self.slugs(), by_name)
        self.assertEqual(self.slugs(ordering="name"), by_name)
        self.assertEqual(self.slugs(ordering="-name"), by_name[::-1])
        # Equal averages (4.0) tie-break on name; unreviewed brands sort last.
        self.assertEqual(
            self.slugs(ordering="-avg_rating"), ["acme-insurance", "zephyr-mobile", "bolt-bank"]
        )
        self.assertEqual(
            self.slugs(ordering="-review_count"), ["zephyr-mobile", "acme-insurance", "bolt-bank"]
        )
        self.assertEqual(
            self.slugs(ordering="review_count"), ["acme-insurance", "zephyr-mobile", "bolt-bank"]
        )
        self.assertEqual(self.slugs(ordering="bogus"), self.slugs(ordering="name"))

    def test_pagination_with_max_page_size(self):
        body = self.get(page_size=2)
        self.assertEqual(len(body["results"]), 2)
        self.assertIsNone(body["previous"])
        self.assertIn("page=2", body["next"])
        page2 = self.get(page_size=2, page=2)
        self.assertEqual([r["slug"] for r in page2["results"]], ["zephyr-mobile"])
        self.assertIsNone(page2["next"])
        for i in range(105):
            make_brand(f"extra-{i:03}")
        self.assertEqual(len(self.get(page_size=1000)["results"]), 100)
        self.assertEqual(self.client.get(URL, {"page": 99}).status_code, 404)

    def test_query_count_constant_per_page(self):
        # count + brands (stats, industry) + top reviews (with reviewer)
        with self.assertNumQueries(3):
            self.get()
        for i in range(20):
            brand = make_brand(f"more-{i:02}", self.telecom)
            make_review(brand, 2, reviewer=self.sarah)
            make_review(brand, 5)
        with self.assertNumQueries(3):
            body = self.get(page_size=20)
        self.assertEqual(len(body["results"]), 20)


class TopReviewRuleTests(TestCase):
    """R7: top review = highest rating, then newest."""

    def test_ties_on_rating_return_the_newest(self):
        brand = make_brand("acme-insurance")
        make_review(brand, 5, days=1)
        new_five = make_review(brand, 5, days=3)
        make_review(brand, 4, days=9)  # newer, but lower rating
        row = self.client.get(URL).json()["results"][0]
        self.assertEqual(row["top_review"]["slug"], new_five.slug)

    def test_brand_with_no_reviews_has_null_top_review(self):
        make_brand("bolt-bank")
        row = self.client.get(URL).json()["results"][0]
        self.assertIsNone(row["top_review"])
        self.assertIsNone(row["average_rating"])
        self.assertEqual(row["review_count"], 0)
