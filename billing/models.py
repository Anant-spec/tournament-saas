from django.db import models
from organizations.models import Organization
import uuid


class Plan(models.Model):
    PLAN_CHOICES = (
        ("free", "Free"),
        ("pro", "Pro"),
        ("business", "Business"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    tournament_limit = models.PositiveIntegerField(default=3)
    team_limit_per_tournament = models.PositiveIntegerField(default=16)
    can_set_entry_fee = models.BooleanField(default=False)
    can_set_prize_pool = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_name_display()


class Subscription(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name}"

    def is_active(self):
        from django.utils import timezone
        if self.status != "active":
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True