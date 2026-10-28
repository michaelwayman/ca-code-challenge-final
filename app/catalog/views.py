"""Server-rendered pages (R3-R5). Slugs match the WP permalinks (C3)."""

from django.shortcuts import get_object_or_404, render

from .models import Brand, Review

HOME_REVIEW_COUNT = 9


def home(request):
    reviews = Review.objects.select_related("brand", "reviewer").order_by("-published_at", "-id")
    return render(request, "catalog/home.html", {"reviews": reviews[:HOME_REVIEW_COUNT]})


def brand_detail(request, slug):
    brand = get_object_or_404(Brand.objects.with_stats().select_related("industry"), slug=slug)
    reviews = brand.reviews.select_related("reviewer").order_by("-published_at", "-id")
    return render(request, "catalog/brand_detail.html", {"brand": brand, "reviews": reviews})


def review_detail(request, slug):
    review = get_object_or_404(Review.objects.select_related("brand", "reviewer"), slug=slug)
    return render(request, "catalog/review_detail.html", {"review": review})
