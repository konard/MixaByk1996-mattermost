"""
Procurement models for GroupBuy Bot
Supports group purchases with organizers, participants, and suppliers
"""
from django.db import models
from django.utils import timezone
from users.models import User


class Category(models.Model):
    """Product category for procurements"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, related_name='children'
    )
    icon = models.CharField(max_length=50, blank=True, help_text='Emoji or icon name')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Procurement(models.Model):
    """Main procurement model"""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        STOPPED = 'stopped', 'Stopped'
        PAYMENT = 'payment', 'Payment in Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    # Basic info
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='procurements')

    # Organizer and supplier
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_procurements')
    supplier = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='supplied_procurements'
    )

    # Location
    city = models.CharField(max_length=100)
    delivery_address = models.TextField(blank=True)

    # Financial
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stop_at_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Stop accepting when this amount is reached'
    )
    unit = models.CharField(max_length=20, default='units', help_text='e.g., kg, pieces, liters')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Status and timing
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    deadline = models.DateTimeField()
    payment_deadline = models.DateTimeField(null=True, blank=True)

    # Metadata
    image_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'procurements'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['organizer']),
            models.Index(fields=['category']),
            models.Index(fields=['city']),
            models.Index(fields=['deadline']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def progress(self):
        """Calculate progress percentage"""
        if self.target_amount == 0:
            return 0
        return min(100, int((self.current_amount / self.target_amount) * 100))

    @property
    def participant_count(self):
        """Get number of participants"""
        return self.participants.count()

    @property
    def days_left(self):
        """Calculate days until deadline"""
        delta = self.deadline - timezone.now()
        return max(0, delta.days)

    @property
    def status_display(self):
        return dict(self.Status.choices).get(self.status, self.status)

    @property
    def can_join(self):
        """Check if new participants can join"""
        if self.status != self.Status.ACTIVE:
            return False
        if self.deadline < timezone.now():
            return False
        if self.stop_at_amount and self.current_amount >= self.stop_at_amount:
            return False
        return True

    def update_current_amount(self):
        """Recalculate current amount from participants"""
        total = self.participants.filter(is_active=True).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.current_amount = total
        self.save(update_fields=['current_amount', 'updated_at'])

        # Check if stop amount is reached
        if self.stop_at_amount and self.current_amount >= self.stop_at_amount:
            self.status = self.Status.STOPPED
            self.save(update_fields=['status', 'updated_at'])


class Participant(models.Model):
    """Participant in a procurement"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PAID = 'paid', 'Paid'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    procurement = models.ForeignKey(Procurement, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='participations')

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    notes = models.TextField(blank=True, help_text='Special requests or notes')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'participants'
        unique_together = ['procurement', 'user']
        indexes = [
            models.Index(fields=['procurement', 'status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user} in {self.procurement.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update procurement totals
        self.procurement.update_current_amount()
