from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Team, Registration
from .forms import TeamForm
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Registration, Team
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse

@login_required
def team_list(request):
    registrations = (
        Registration.objects
        .select_related("team", "tournament", "tournament__organization")
        .filter(tournament__organization__owner=request.user)
        .order_by("-created_at")
    )

    paginator = Paginator(registrations, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "registrations/team_list.html", {
        "page_obj": page_obj,
        "registrations": page_obj,
        "total_registrations": registrations.count(),
        "approved_count": registrations.filter(status="approved").count(),
        "pending_count": registrations.filter(status="pending").count(),
        "rejected_count": registrations.filter(status="rejected").count(),
    })

@login_required
def team_create(request):
    form = TeamForm(request.POST or None)

    form.fields["tournament"].queryset = form.fields["tournament"].queryset.filter(
        organization__owner=request.user
    )

    if form.is_valid():
        tournament = form.cleaned_data["tournament"]

        # CHECK 1 — registration open
        if not tournament.registration_open:
            messages.error(request, "Registration is closed for this tournament.")
            return render(request, "registrations/team_form.html", {"form": form})

        # CHECK 2 — max teams not exceeded
        approved_count = Registration.objects.filter(
            tournament=tournament,
            status="approved"
        ).count()

        if approved_count >= tournament.max_teams:
            messages.error(request, f"This tournament has reached its maximum of {tournament.max_teams} approved teams.")
            return render(request, "registrations/team_form.html", {"form": form})

        team = form.save()

        Registration.objects.create(
            tournament=tournament,
            team=team,
            status="pending"
        )

        messages.success(request, f"{team.name} registered successfully. Awaiting approval.")
        return redirect("team_list")

    return render(request, "registrations/team_form.html", {
        "form": form
    })


@login_required
@require_POST
def approve_registration(request, pk):
    registration = get_object_or_404(
        Registration.objects.select_related("tournament__organization", "team"),
        pk=pk,
        tournament__organization__owner=request.user,
    )

    page = request.POST.get("page", "1")

    if registration.tournament.matches.exists():
        messages.error(request, "Cannot change registration status after bracket has been generated.")
        return redirect(f"{reverse('team_list')}?page={page}")

    if registration.status == "approved":
        messages.info(request, f"{registration.team.name} is already approved.")
        return redirect(f"{reverse('team_list')}?page={page}")

    registration.status = "approved"
    registration.approved_at = timezone.now()
    registration.save(update_fields=["status", "approved_at"])

    messages.success(request, f"{registration.team.name} approved successfully.")
    return redirect(f"{reverse('team_list')}?page={page}")


@login_required
@require_POST
def reject_registration(request, pk):
    registration = get_object_or_404(
        Registration.objects.select_related("tournament__organization", "team"),
        pk=pk,
        tournament__organization__owner=request.user,
    )

    page = request.POST.get("page", "1")

    if registration.tournament.matches.exists():
        messages.error(request, "Cannot change registration status after bracket has been generated.")
        return redirect(f"{reverse('team_list')}?page={page}")

    if registration.status == "rejected":
        messages.info(request, f"{registration.team.name} is already rejected.")
        return redirect(f"{reverse('team_list')}?page={page}")

    registration.status = "rejected"
    registration.rejected_at = timezone.now()
    registration.save(update_fields=["status", "rejected_at"])

    messages.success(request, f"{registration.team.name} rejected successfully.")
    return redirect(f"{reverse('team_list')}?page={page}")




@login_required
def player_create(request, team_id):
    team = get_object_or_404(
        Team,
        pk=team_id,
        tournament__organization__owner=request.user
    )

    from .forms import PlayerForm
    from .models import Player

    form = PlayerForm(request.POST or None)

    if form.is_valid():
        player = form.save(commit=False)
        player.team = team
        player.save()
        messages.success(request, f"{player.in_game_name} added to {team.name}.")
        return redirect("team_players", team_id=team.pk)

    return render(request, "registrations/player_form.html", {
        "form": form,
        "team": team,
    })


@login_required
def team_players(request, team_id):
    team = get_object_or_404(
        Team,
        pk=team_id,
        tournament__organization__owner=request.user
    )
    players = team.players.all().order_by("role", "created_at")

    return render(request, "registrations/team_players.html", {
        "team": team,
        "players": players,
    })


def public_register(request, org_slug, tournament_slug):
    from tournaments.models import Tournament
    from organizations.models import Organization

    org = get_object_or_404(Organization, slug=org_slug)
    tournament = get_object_or_404(
        Tournament,
        slug=tournament_slug,
        organization=org,
        status__in=["draft", "published"]
    )

    # Block if registration is closed
    if not tournament.registration_open:
        return render(request, "registrations/registration_closed.html", {
            "tournament": tournament
        })

    # Block if max teams already approved
    approved_count = Registration.objects.filter(
        tournament=tournament, status="approved"
    ).count()
    if approved_count >= tournament.max_teams:
        return render(request, "registrations/registration_closed.html", {
            "tournament": tournament,
            "reason": "full"
        })

    from .forms import PublicTeamForm
    form = PublicTeamForm(request.POST or None)

    if form.is_valid():
        team = form.save(commit=False)
        team.tournament = tournament
        team.save()
        Registration.objects.create(tournament=tournament, team=team, status="pending")
        return render(request, "registrations/registration_success.html", {
            "team": team,
            "tournament": tournament
        })

    return render(request, "registrations/public_register.html", {
        "form": form,
        "tournament": tournament,
        "org": org,
    })