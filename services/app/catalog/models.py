"""Brands, reviews, industries and reviewers (R1). Every WP-sourced row carries the WP id
it came from (wp_id, unique) so import_wp can re-run as an upsert; slug is an attribute."""

from django.db import models
from django.db.models import Avg, Count


class Industry(models.Model):
    wp_id = models.PositiveIntegerField(unique=True, help_text="wp_terms.term_id")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "industries"

    def __str__(self):
        return self.name


class Reviewer(models.Model):
    """Public profile of a review author. The pk is the auth service user id,
    wp_user_uuid(wp_user_id), so no WP id or credentials live here (C2)."""

    id = models.UUIDField(primary_key=True)
    display_name = models.CharField(max_length=250)

    def __str__(self):
        return self.display_name


class BrandQuerySet(models.QuerySet):
    def with_stats(self):
        """average_rating is derived from reviews, never stored (R1)."""
        return self.annotate(average_rating=Avg("reviews__rating"), review_count=Count("reviews"))


class Brand(models.Model):
    wp_id = models.PositiveIntegerField(unique=True, help_text="wp_posts.ID")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, help_text="HTML from post_content")
    excerpt = models.TextField(blank=True)
    short_description = models.TextField(
        null=True,
        blank=True,
        help_text="Editor-set (R8), shown as is; NULL derives it from excerpt/description",
    )
    industry = models.ForeignKey(
        Industry, null=True, blank=True, on_delete=models.SET_NULL, related_name="brands"
    )
    website_url = models.URLField(blank=True)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    headquarters = models.CharField(max_length=200, blank=True)
    legacy_average_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="ACF average_rating as entered in WP; audit only",
    )
    seo_title = models.CharField(max_length=300, blank=True, help_text="_yoast_wpseo_title")
    seo_description = models.TextField(blank=True, help_text="_yoast_wpseo_metadesc")
    published_at = models.DateTimeField()
    modified_at = models.DateTimeField()

    objects = BrandQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Review(models.Model):
    wp_id = models.PositiveIntegerField(unique=True, help_text="wp_posts.ID")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        Reviewer, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews"
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField(blank=True, help_text="HTML from post_content")
    rating = models.PositiveSmallIntegerField()
    reviewer_location = models.CharField(max_length=200, blank=True)
    published_at = models.DateTimeField()
    modified_at = models.DateTimeField()

    class Meta:
        ordering = ["-published_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_1_to_5"
            ),
        ]

    def __str__(self):
        return self.title
