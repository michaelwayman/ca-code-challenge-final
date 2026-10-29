"""Brand API. The listing (R6) is public; each page costs a fixed number of queries: one
count, one for brands with their stats and industry, one for every brand's top review (R7).
A single brand is public to read and editable by editors, short_description only (R8)."""

from cauth.drf import IsEditor
from django.db.models import F, Prefetch, Window
from django.db.models.functions import NullIf, RowNumber
from rest_framework import generics, pagination, permissions
from rest_framework.response import Response

from config.auth import AuthServiceJWT

from .models import Brand, Review
from .serializers import BrandEditSerializer, BrandListSerializer

DEFAULT_ORDERING = "name"

# ?ordering= value -> sort expression; a leading "-" reverses it.
ORDERINGS = {
    "name": F("name"),
    "avg_rating": F("average_rating"),
    # NULL for zero reviews so nulls_last puts unreviewed brands last in both directions.
    "review_count": NullIf(F("review_count"), 0),
}


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
        value = self.request.query_params.get("ordering", DEFAULT_ORDERING)
        key = value.removeprefix("-")
        if key not in ORDERINGS:
            value, key = DEFAULT_ORDERING, DEFAULT_ORDERING
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
