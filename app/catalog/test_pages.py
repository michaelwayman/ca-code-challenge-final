from datetime import UTC, datetime

from django.test import TestCase

from .models import Brand, Industry, Review


def make_brand(n=1, **kw):
    now = datetime(2024, 1, n, tzinfo=UTC)
    ind, _ = Industry.objects.get_or_create(
        wp_id=1, defaults={"name": "Banking", "slug": "banking"}
    )
    return Brand.objects.create(
        wp_id=n, name=f"Brand {n}", slug=f"brand-{n}", industry=ind, published_at=now,
        modified_at=now, website_url="https://example.com", founded_year=1990,
        headquarters="Berlin", **kw,
    )  # fmt: skip


def make_review(brand, n, rating=4):
    d = datetime(2024, 2, n, tzinfo=UTC)
    return Review.objects.create(
        wp_id=100 + n, brand=brand, title=f"Review {n}", slug=f"review-{n}",
        body=f"<p>Body {n}</p>", rating=rating, published_at=d, modified_at=d,
    )  # fmt: skip


class PageTests(TestCase):
    def test_home_empty_state(self):
        r = self.client.get("/")
        self.assertContains(r, "hero")
        self.assertContains(r, "No reviews yet")

    def test_home_newest_first(self):
        b = make_brand()
        for n in (1, 3, 2):
            make_review(b, n)
        body = self.client.get("/").content.decode()
        self.assertLess(body.index("Review 3"), body.index("Review 2"))
        self.assertLess(body.index("Review 2"), body.index("Review 1"))

    def test_brand_page(self):
        b = make_brand()
        make_review(b, 1, 5)
        make_review(b, 2, 3)
        r = self.client.get("/brand/brand-1/")
        for text in (
            "Brand 1",
            "Banking",
            "https://example.com",
            "1990",
            "Berlin",
            "4.0",
            "Review 1",
        ):
            self.assertContains(r, text)

    def test_review_page(self):
        b = make_brand()
        make_review(b, 1)
        r = self.client.get("/review/review-1/")
        self.assertContains(r, "Review 1")
        self.assertContains(r, "Body 1")
        self.assertContains(r, 'href="/brand/brand-1/"')

    def test_unknown_slugs_404(self):
        self.assertEqual(self.client.get("/brand/nope/").status_code, 404)
        self.assertEqual(self.client.get("/review/nope/").status_code, 404)


class SharedFormattingTests(TestCase):
    """Pages and the API must show the same stars and excerpts for the same data."""

    def test_half_stars_round_up_like_the_react_list(self):
        brand = make_brand()
        for n, rating in enumerate([2, 3], start=1):
            make_review(brand, n, rating=rating)
        html = self.client.get("/brand/brand-1/").content.decode()
        hero = html.split('class="brand-hero"')[1].split("</section>")[0]
        self.assertEqual(hero.count("star-full"), 3)
        self.assertIn('aria-label="Rated 2.5 out of 5"', hero)
        self.assertIn('<span class="rating-value" aria-hidden="true">2.5</span>', hero)

    def test_api_rounds_average_half_up(self):
        brand = make_brand()
        for n, rating in enumerate([2, 2, 2, 3], start=1):
            make_review(brand, n, rating=rating)
        row = self.client.get("/api/brands/").json()["results"][0]
        self.assertEqual(row["average_rating"], 2.3)

    def test_review_card_excerpt_keeps_bare_ampersands(self):
        review = make_review(make_brand(), 1)
        review.body = "<p>Tom &amp; Jerry at AT&T</p>"
        review.save()
        self.assertContains(self.client.get("/"), "Tom &amp; Jerry at AT&amp;T")
