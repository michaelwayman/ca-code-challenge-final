from django.urls import path

from accounts import views

urlpatterns = [
    path("auth/login", views.login, name="login"),
    path(".well-known/jwks.json", views.jwks, name="jwks"),
    path("healthz", views.healthz, name="healthz"),
]
