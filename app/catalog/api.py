"""Brand API. The listing is public; each page costs a fixed number of queries: one count,
one for brands with their stats and industry, one for every brand's top review. A single
brand is public to read and editable by editors, short_description only."""

from django.db.models import F
from django.db.models.functions import NullIf
from rest_framework import generics, pagination, permissions
from rest_framework.response import Response
from shared_auth.drf import IsEditor

from .auth import AuthServiceJWT
from .models import Brand
from .serializers import BrandEditSerializer, BrandSerializer

# ?ordering= value -> sort expression; a leading "-" reverses it.
ORDERINGS = {
    "name": F("name"),
    "avg_rating": F("average_rating"),
    # NULL for zero reviews so nulls_last puts unreviewed brands last in both directions.
    "review_count": NullIf(F("review_count"), 0),
}


class BrandPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BrandList(generics.ListAPIView):
    """GET /api/brands/?industry=<slug>&industry=...&ordering=-avg_rating&page=2&page_size=10"""

    serializer_class = BrandSerializer
    pagination_class = BrandPagination

    def list(self, request, *args, **kwargs):
        # The listing is public and read-only: let browsers reuse repeat filter/sort/page URLs.
        response = super().list(request, *args, **kwargs)
        response["Cache-Control"] = "public, max-age=30, stale-while-revalidate=120"
        return response

    def get_queryset(self):
        brands = Brand.objects.for_api()
        # Blank values (a cleared filter form sends ?industry=) mean "no filter".
        industries = [s for s in self.request.query_params.getlist("industry") if s]
        if industries:
            brands = brands.filter(industry__slug__in=industries)
        return brands.order_by(*self.ordering())

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

    serializer_class = BrandSerializer
    lookup_field = "slug"
    http_method_names = ["get", "patch", "head", "options"]

    def is_read_only(self):
        return self.request.method in permissions.SAFE_METHODS

    def get_authenticators(self):
        # Reads never look at the token, so they work with a stale one or with auth down.
        return [] if self.is_read_only() else [AuthServiceJWT()]

    def get_permissions(self):
        return [permissions.AllowAny()] if self.is_read_only() else [IsEditor()]

    def get_queryset(self):
        return Brand.objects.for_api()

    def partial_update(self, request, *args, **kwargs):
        edit = BrandEditSerializer(self.get_object(), data=request.data)
        edit.is_valid(raise_exception=True)
        edit.save()
        return Response(self.get_serializer(self.get_object()).data)
