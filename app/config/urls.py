from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_GET

from catalog import views
from catalog.api import BrandDetail, BrandList


@require_GET
def healthz(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"detail": "database unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


api_patterns = [
    path("brands/", BrandList.as_view(), name="brand-list"),
    path("brands/<slug:slug>/", BrandDetail.as_view(), name="brand-detail"),
]

urlpatterns = [
    path("", views.home, name="home"),
    path("brands/", views.brand_list, name="brand-list"),
    path("brand/<slug:slug>/", views.brand_detail, name="brand-detail"),
    path("review/<slug:slug>/", views.review_detail, name="review-detail"),
    path("healthz", healthz, name="healthz"),
    path("api/", include((api_patterns, "api"))),
]
