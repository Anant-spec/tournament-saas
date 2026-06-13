from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from organizations.models import Organization
from tournaments.models import Tournament
from registrations.models import Registration

def home(request):
    return render(request, "core/home.html")

@login_required
def dashboard(request):
    organizations = Organization.objects.filter(owner=request.user)
    tournaments = Tournament.objects.filter(organization__owner=request.user)
    registrations = Registration.objects.filter(tournament__organization__owner=request.user)

    context = {
        "total_organizations": organizations.count(),
        "total_tournaments": tournaments.count(),
        "ongoing_tournaments": tournaments.filter(status="ongoing").count(),
        "completed_tournaments": tournaments.filter(status="completed").count(),
        "draft_tournaments": tournaments.filter(status="draft").count(),
        "total_registrations": registrations.count(),
        "recent_tournaments": tournaments.order_by("-created_at")[:5],
    }

    return render(request, "core/dashboard.html", context)