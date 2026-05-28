from django.db import models
from organizations.models import Organization
import uuid

class Tournament(models.Model):
    FORMAT_CHOICES = (
        ("single_elimination", "Single Elimination"),
        ("round_robin", "Round Robin"),
    )

    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="tournaments")
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    game_title = models.CharField(max_length=100)
    format_type = models.CharField(max_length=30, choices=FORMAT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    champion = models.ForeignKey(
        "registrations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_tournaments"
    )
    registration_open = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "slug")

    def __str__(self):
        return self.name



class Match(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")
    round_number = models.PositiveIntegerField()
    match_number = models.PositiveIntegerField()
    team1 = models.ForeignKey(
        "registrations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_team1"
    )
    team2 = models.ForeignKey(
        "registrations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_team2"
    )
    winner = models.ForeignKey(
        "registrations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_matches"
    )
    next_match = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_matches"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["round_number", "match_number"]

    def __str__(self):
        return f"{self.tournament.name} - Round {self.round_number} Match {self.match_number}"