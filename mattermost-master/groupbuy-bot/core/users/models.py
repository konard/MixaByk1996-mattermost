"""
User models for GroupBuy Bot
Supports three roles: buyer, organizer, supplier
"""
from django.db import models
from django.core.validators import RegexValidator


class User(models.Model):
    """User model with support for multiple messenger platforms"""

    class Role(models.TextChoices):
        BUYER = 'buyer', 'Buyer'
        ORGANIZER = 'organizer', 'Organizer'
        SUPPLIER = 'supplier', 'Supplier'

    class Platform(models.TextChoices):
        TELEGRAM = 'telegram', 'Telegram'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        WEBSOCKET = 'websocket', 'WebSocket'
        VK = 'vk', 'VKontakte'

    # Platform identification
    platform = models.CharField(max_length=20, choices=Platform.choices, default=Platform.TELEGRAM)
    platform_user_id = models.CharField(max_length=100, db_index=True)

    # User info
    username = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)

    # Contact info
    phone_regex = RegexValidator(
        regex=r'^\+?[1-9]\d{10,14}$',
        message="Phone number must be in format: '+79991234567'"
    )
    phone = models.CharField(validators=[phone_regex], max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Role and balance
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUYER)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Metadata
    language_code = models.CharField(max_length=10, default='ru')
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        unique_together = ['platform', 'platform_user_id']
        indexes = [
            models.Index(fields=['platform', 'platform_user_id']),
            models.Index(fields=['role']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.platform}:{self.platform_user_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def role_display(self):
        return dict(self.Role.choices).get(self.role, self.role)

    def update_balance(self, amount):
        """Update user balance (positive for credit, negative for debit)"""
        self.balance += amount
        self.save(update_fields=['balance', 'updated_at'])
        return self.balance


class UserSession(models.Model):
    """User session for tracking dialog states"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    dialog_type = models.CharField(max_length=50, blank=True)
    dialog_state = models.CharField(max_length=50, blank=True)
    dialog_data = models.JSONField(default=dict)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user', 'dialog_type']),
        ]

    def __str__(self):
        return f"Session for {self.user} - {self.dialog_type}"
