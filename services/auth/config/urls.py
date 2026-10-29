from django.contrib import admin
from django.urls import path

from accounts import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/login", views.login, name="login"),
    path("auth/refresh", views.refresh, name="refresh"),
    path("auth/logout", views.logout, name="logout"),
    path(".well-known/jwks.json", views.jwks, name="jwks"),
    path("healthz", views.healthz, name="healthz"),
]
