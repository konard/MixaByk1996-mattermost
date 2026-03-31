"""
Serializers for User API
"""
from rest_framework import serializers
from .models import User, UserSession


class UserSerializer(serializers.ModelSerializer):
    """User serializer for read operations"""
    role_display = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'platform', 'platform_user_id', 'username',
            'first_name', 'last_name', 'full_name', 'phone', 'email',
            'role', 'role_display', 'balance', 'language_code',
            'is_active', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'is_verified', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    class Meta:
        model = User
        fields = [
            'platform', 'platform_user_id', 'username',
            'first_name', 'last_name', 'phone', 'email',
            'role', 'language_code'
        ]

    def validate_phone(self, value):
        if value and not value.startswith('+'):
            value = '+' + value
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for profile updates"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email', 'role']


class UserBalanceSerializer(serializers.Serializer):
    """Serializer for balance information"""
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_deposited = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    available = serializers.DecimalField(max_digits=12, decimal_places=2)


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions"""

    class Meta:
        model = UserSession
        fields = ['id', 'dialog_type', 'dialog_state', 'dialog_data', 'expires_at', 'created_at']


class CheckAccessSerializer(serializers.Serializer):
    """Serializer for access check requests"""
    user_id = serializers.IntegerField()
