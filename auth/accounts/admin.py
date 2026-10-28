from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import RefreshToken, User


@admin.register(User)
class AccountAdmin(UserAdmin):
    # Role is the only authorization the main app sees; operators edit it here.
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role", {"fields": ("role",)}),)


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__username",)
    readonly_fields = ("user", "token_hash", "created_at", "expires_at", "revoked_at")
    actions = ["revoke"]

    def has_add_permission(self, request):
        return False  # raw tokens are only ever issued by login

    @admin.action(description="Revoke selected refresh tokens")
    def revoke(self, request, queryset):
        count = queryset.revoke()
        self.message_user(request, f"Revoked {count} refresh token(s).")
