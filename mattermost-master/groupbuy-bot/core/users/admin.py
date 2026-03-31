from django.contrib import admin
from .models import User, UserSession


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'platform', 'role', 'balance', 'is_active', 'created_at']
    list_filter = ['platform', 'role', 'is_active', 'is_verified']
    search_fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'platform_user_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'dialog_type', 'dialog_state', 'created_at']
    list_filter = ['dialog_type']
    search_fields = ['user__first_name', 'user__platform_user_id']
