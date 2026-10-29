"""Representations of brands and reviews for the API (R6, R8)."""

from typing import Any

from rest_framework import serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from .models import Brand, Industry, Review
from .text import snippet


class IndustrySerializer(serializers.Serializer[Industry]):
    name = serializers.CharField()
    slug = serializers.CharField()


class TopReviewSerializer(serializers.Serializer[Review]):
    title = serializers.CharField()
    slug = serializers.CharField()
    rating = serializers.IntegerField()
    reviewer = serializers.CharField(source="reviewer.display_name", default=None)
    published_at = serializers.DateTimeField()
    snippet = serializers.SerializerMethodField()

    def get_snippet(self, review: Review) -> str:
        return snippet(review.body)


class BrandListSerializer(serializers.Serializer[Brand]):
    name = serializers.CharField()
    slug = serializers.CharField()
    industry = IndustrySerializer(allow_null=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField()
    short_description = serializers.SerializerMethodField()
    top_review = serializers.SerializerMethodField()

    def get_average_rating(self, brand: Brand) -> float | None:
        return None if brand.average_rating is None else round(brand.average_rating, 1)

    def get_short_description(self, brand: Brand) -> str:
        # An editor's value, blank included, is returned exactly as saved.
        if brand.short_description is not None:
            return brand.short_description
        return snippet(brand.excerpt or brand.description)

    def get_top_review(self, brand: Brand) -> ReturnDict[str, Any] | None:
        top = brand.top_reviews[0] if brand.top_reviews else None
        return TopReviewSerializer(top).data if top else None


class BrandEditSerializer(serializers.Serializer[Brand]):
    """The one writable field. It has its own column so it round-trips verbatim and a WP
    re-import (which rewrites excerpt) keeps it. Any other key is rejected, not ignored."""

    short_description = serializers.CharField(
        allow_blank=True, max_length=1000, trim_whitespace=False
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({key: "This field is read-only." for key in unknown})
        return attrs

    def update(self, brand: Brand, validated_data: dict[str, Any]) -> Brand:
        brand.short_description = validated_data["short_description"]
        brand.save(update_fields=["short_description"])
        return brand
