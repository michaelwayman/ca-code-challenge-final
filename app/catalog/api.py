"""Brand API. The listing (R6) is public; each page costs a fixed number of queries: one
count, one for brands with their stats and industry, one for every brand's top review (R7).
A single brand is public to read and editable by editors, short_description only (R8)."""

from html.parser import HTMLParser

from cauth.drf import IsEditor
from django.db.models import F, Prefetch, Window
from django.db.models.functions import NullIf, RowNumber
from django.utils.text import Truncator
from rest_framework import generics, pagination, permissions, serializers
from rest_framework.response import Response

from config.auth import AuthServiceJWT

from .models import Brand, Review

SNIPPET_WORDS = 30

# ?ordering= value -> sort expression; a leading "-" reverses it.
ORDERINGS = {
    "name": F("name"),
    "avg_rating": F("average_rating"),
    # NULL for zero reviews so nulls_last puts unreviewed brands last in both directions.
    "review_count": NullIf(F("review_count"), 0),
}


class _TextExtractor(HTMLParser):
    """Collects text outside tags with entities decoded. Unlike strip_tags + unescape,
    a bare ampersand ("AT&T") stays as written instead of becoming "AT&T;"."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def snippet(html):
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return Truncator("".join(parser.parts)).words(SNIPPET_WORDS)


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


class BrandPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def brands():
    return (
        Brand.objects.with_stats()
        .select_related("industry")
        .prefetch_related(top_review_prefetch())
    )


class BrandList(generics.ListAPIView):
    """GET /api/brands/?industry=<slug>&industry=...&ordering=-avg_rating&page=2&page_size=10"""

    serializer_class = BrandListSerializer
    pagination_class = BrandPagination

    def list(self, request, *args, **kwargs):
        # The listing is public and read-only: let browsers reuse repeat filter/sort/page URLs.
        response = super().list(request, *args, **kwargs)
        response["Cache-Control"] = "public, max-age=30, stale-while-revalidate=120"
        return response

    def get_queryset(self):
        qs = brands()
        # Blank values (a cleared filter form sends ?industry=) mean "no filter".
        industries = [s for s in self.request.query_params.getlist("industry") if s]
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


class BrandDetail(generics.RetrieveUpdateAPIView):
    """GET /api/brands/<slug>/ is public; PATCH needs an editor token. No PUT."""

    serializer_class = BrandListSerializer
    lookup_field = "slug"
    http_method_names = ["get", "patch", "head", "options"]

    def reading(self):
        return self.request.method in permissions.SAFE_METHODS

    def get_authenticators(self):
        # Reads never look at the token, so they work with a stale one or with auth down (R9).
        return [] if self.reading() else [AuthServiceJWT()]

    def get_permissions(self):
        return [permissions.AllowAny()] if self.reading() else [IsEditor()]

    def get_queryset(self):
        return brands()

    def partial_update(self, request, *args, **kwargs):
        edit = BrandEditSerializer(self.get_object(), data=request.data)
        edit.is_valid(raise_exception=True)
        edit.save()
        return Response(self.get_serializer(self.get_object()).data)
