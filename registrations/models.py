from django.db import models
from tournaments.models import Tournament
import uuid

class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=255)
    captain_name = models.CharField(max_length=255)
    captain_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Registration(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="registrations")
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name="registration")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.team.name} - {self.tournament.name}"




class Player(models.Model):
    ROLE_CHOICES = (
        ("captain", "Captain"),
        ("player", "Player"),
        ("substitute", "Substitute"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    full_name = models.CharField(max_length=255)
    in_game_name = models.CharField(max_length=100)
    game_uid = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="player")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.in_game_name} ({self.team.name})"