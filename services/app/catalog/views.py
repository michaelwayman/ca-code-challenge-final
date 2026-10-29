"""Server-rendered pages (R3-R5). Slugs match the WP permalinks (C3)."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Brand, Industry, Review

HOME_REVIEW_COUNT = 9


def home(request: HttpRequest) -> HttpResponse:
    reviews = Review.objects.select_related("brand", "reviewer").order_by("-published_at", "-id")
    return render(request, "catalog/home.html", {"reviews": reviews[:HOME_REVIEW_COUNT]})


def brand_detail(request: HttpRequest, slug: str) -> HttpResponse:
    brand = get_object_or_404(Brand.objects.with_stats().select_related("industry"), slug=slug)
    reviews = brand.reviews.select_related("reviewer").order_by("-published_at", "-id")
    return render(request, "catalog/brand_detail.html", {"brand": brand, "reviews": reviews})


def review_detail(request: HttpRequest, slug: str) -> HttpResponse:
    review = get_object_or_404(Review.objects.select_related("brand", "reviewer"), slug=slug)
    return render(request, "catalog/review_detail.html", {"review": review})


def brand_list(request: HttpRequest) -> HttpResponse:
    """Mount point for the React BrandList (R26); it reads the industry options from json_script."""
    with_brands = Industry.objects.filter(brands__isnull=False).distinct()
    industries = list(with_brands.values("slug", "name"))
    return render(request, "catalog/brand_list.html", {"industries": industries})
