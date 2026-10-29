from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.urls import path
from django.views.decorators.http import require_GET

from catalog import views
from catalog.api import BrandDetail, BrandList


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"detail": "database unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", views.home, name="home"),
    path("brands/", views.brand_list, name="brand-list-page"),
    path("brand/<slug:slug>/", views.brand_detail, name="brand-page"),
    path("review/<slug:slug>/", views.review_detail, name="review-page"),
    path("healthz", healthz, name="healthz"),
    path("api/brands/", BrandList.as_view(), name="brand-list"),
    path("api/brands/<slug:slug>/", BrandDetail.as_view(), name="brand-detail"),
]
