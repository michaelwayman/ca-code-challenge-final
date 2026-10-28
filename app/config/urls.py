from django.db import connection
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.http import require_GET

from catalog.api import BrandDetail, BrandList


@require_GET
def healthz(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"detail": "database unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("api/brands/", BrandList.as_view(), name="brand-list"),
    path("api/brands/<slug:slug>/", BrandDetail.as_view(), name="brand-detail"),
]
