"""Public brand listing API (R6). Each page costs a fixed number of queries: one count,
one for brands with their stats and industry, one for every brand's top review (R7)."""

from django.db.models import F, Prefetch, Window
from django.db.models.functions import RowNumber
from django.utils.html import strip_tags
from django.utils.text import Truncator
from rest_framework import generics, pagination, serializers

from .models import Brand, Review

SNIPPET_WORDS = 30

# ?ordering= value -> sort expression; a leading "-" reverses it.
ORDERINGS = {
    "name": F("name"),
    "avg_rating": F("average_rating"),
    "review_count": F("review_count"),
}


def snippet(html):
    return Truncator(strip_tags(html)).words(SNIPPET_WORDS)


def top_review_prefetch():
    """Top review = highest rating, then newest (published_at, then wp_id as the last
    tie-break). One windowed query covers every brand on the page."""
    ranked = (
        Review.objects.select_related("reviewer")
        .annotate(
            rank=Window(
                RowNumber(),
                partition_by=F("brand_id"),
                order_by=[F("rating").desc(), F("published_at").desc(), F("wp_id").desc()],
            )
        )
        .filter(rank=1)
    )
    return Prefetch("reviews", queryset=ranked, to_attr="top_reviews")


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


class BrandListSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    industry = IndustrySerializer(allow_null=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField()
    short_description = serializers.SerializerMethodField()
    top_review = serializers.SerializerMethodField()

    def get_average_rating(self, brand):
        return None if brand.average_rating is None else round(brand.average_rating, 1)

    def get_short_description(self, brand):
        return snippet(brand.excerpt or brand.description)

    def get_top_review(self, brand):
        top = brand.top_reviews[0] if brand.top_reviews else None
        return TopReviewSerializer(top).data if top else None


class BrandPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BrandList(generics.ListAPIView):
    """GET /api/brands/?industry=<slug>&industry=...&ordering=-avg_rating&page=2&page_size=10"""

    serializer_class = BrandListSerializer
    pagination_class = BrandPagination

    def get_queryset(self):
        qs = (
            Brand.objects.with_stats()
            .select_related("industry")
            .prefetch_related(top_review_prefetch())
        )
        industries = self.request.query_params.getlist("industry")
        if industries:
            qs = qs.filter(industry__slug__in=industries)
        return qs.order_by(*self.ordering())

    def ordering(self):
        """Unknown values fall back to name. Brands without reviews sort last either way;
        name and id break ties so pages never overlap."""
        value = self.request.query_params.get("ordering", "name")
        key = value.removeprefix("-")
        if key not in ORDERINGS:
            value, key = "name", "name"
        expr = ORDERINGS[key]
        first = expr.desc(nulls_last=True) if value.startswith("-") else expr.asc(nulls_last=True)
        return [first, "name", "id"]
