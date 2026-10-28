from rest_framework import serializers

from .formatting import one_decimal, snippet


class IndustrySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()


class TopReviewSerializer(serializers.Serializer):
    title = serializers.CharField()
    slug = serializers.CharField()
    rating = serializers.IntegerField()
    reviewer = serializers.CharField(source="reviewer.display_name", default=None)
    published_at = serializers.DateTimeField()
    snippet = serializers.SerializerMethodField()

    def get_snippet(self, review):
        return snippet(review.body)


class BrandSerializer(serializers.Serializer):
    """A brand as the listing and detail endpoints return it. Expects Brand.objects.for_api()."""

    name = serializers.CharField()
    slug = serializers.CharField()
    industry = IndustrySerializer(allow_null=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField()
    short_description = serializers.SerializerMethodField()
    top_review = serializers.SerializerMethodField()

    def get_average_rating(self, brand):
        rating = one_decimal(brand.average_rating)
        return None if rating is None else float(rating)

    def get_short_description(self, brand):
        # An editor's value, blank included, is returned exactly as saved.
        if brand.short_description is not None:
            return brand.short_description
        return snippet(brand.excerpt or brand.description)

    def get_top_review(self, brand):
        top = brand.top_reviews[0] if brand.top_reviews else None
        return TopReviewSerializer(top).data if top else None


class BrandEditSerializer(serializers.Serializer):
    """The one writable field. It has its own column so it round-trips verbatim and a WP
    re-import (which rewrites excerpt) keeps it. Any other key is rejected, not ignored."""

    short_description = serializers.CharField(
        allow_blank=True, max_length=1000, trim_whitespace=False
    )

    def validate(self, attrs):
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({key: "This field is read-only." for key in unknown})
        return attrs

    def update(self, brand, validated_data):
        brand.short_description = validated_data["short_description"]
        brand.save(update_fields=["short_description"])
        return brand
