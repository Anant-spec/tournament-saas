from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from organizations.models import Organization
from tournaments.models import Tournament
from registrations.models import Team

def home(request):
    return render(request, "core/home.html")

@login_required
def dashboard(request):
    organizations = Organization.objects.filter(owner=request.user)
    tournaments = Tournament.objects.filter(organization__owner=request.user)
    teams = Team.objects.filter(tournament__organization__owner=request.user)

    context = {
        "organization_count": organizations.count(),
        "tournament_count": tournaments.count(),
        "team_count": teams.count(),
        "recent_organizations": organizations.order_by("-created_at")[:5],
        "recent_tournaments": tournaments.order_by("-created_at")[:5],
        "recent_teams": teams.order_by("-created_at")[:5],
    }
    return render(request, "core/dashboard.html", context)