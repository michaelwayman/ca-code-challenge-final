from datetime import UTC, datetime

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import RefreshToken, User


@admin.register(User)
class AccountAdmin(UserAdmin):  # type: ignore[type-arg]  # UserAdmin is not subscriptable at runtime
    # Role is the only authorization the main app sees (R13); operators edit it here.
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = (*(UserAdmin.fieldsets or ()), ("Role", {"fields": ("role",)}))
    add_fieldsets = (*(UserAdmin.add_fieldsets or ()), ("Role", {"fields": ("role",)}))


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):  # type: ignore[type-arg]  # not subscriptable at runtime
    list_display = ("user", "created_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__username",)
    readonly_fields = ("user", "token_hash", "created_at", "expires_at", "revoked_at")
    actions = ["revoke"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False  # raw tokens are only ever issued by login

    @admin.action(description="Revoke selected refresh tokens")
    def revoke(self, request: HttpRequest, queryset: QuerySet[RefreshToken]) -> None:
        count = queryset.filter(revoked_at__isnull=True).update(revoked_at=datetime.now(UTC))
        self.message_user(request, f"Revoked {count} refresh token(s).")
