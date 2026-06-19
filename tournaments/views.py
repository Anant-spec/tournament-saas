import math
import random
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Tournament, Match
from organizations.models import Organization
from .forms import TournamentForm
from registrations.models import Team
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator

@login_required
def tournament_list(request):
    tournaments = (
        Tournament.objects
        .filter(organization__owner=request.user)
        .select_related("organization", "champion")
        .order_by("-created_at")
    )

    paginator = Paginator(tournaments, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "tournaments/tournament_list.html", {
        "page_obj": page_obj,
        "tournaments": page_obj,
    })

@login_required
def tournament_create(request):
    form = TournamentForm(request.POST or None, user=request.user)

    if form.is_valid():
        tournament = form.save(commit=False)

        org = tournament.organization
        try:
            sub = org.subscription
            active_count = Tournament.objects.filter(organization=org).count()
            if active_count >= sub.plan.tournament_limit:
                messages.error(request, f"Your {sub.plan.get_name_display()} plan allows only {sub.plan.tournament_limit} tournaments. Upgrade to create more.")
                return render(request, "tournaments/tournament_form.html", {"form": form})
        except Exception:
            messages.error(request, "No active plan found for your organization. Please set up a plan.")
            return render(request, "tournaments/tournament_form.html", {"form": form})

        from django.utils.text import slugify
        base_slug = slugify(tournament.name)
        slug = base_slug
        counter = 1

        while Tournament.objects.filter(organization=tournament.organization, slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        tournament.slug = slug
        tournament.save()

        return redirect("tournament_list")

    return render(request, "tournaments/tournament_form.html", {
        "form": form
    })

@login_required
def tournament_edit(request, pk):
    tournament = get_object_or_404(
        Tournament,
        pk=pk,
        organization__owner=request.user
    )

    form = TournamentForm(
        request.POST or None,
        instance=tournament,
        user=request.user
    )

    if form.is_valid():
        form.save()
        messages.success(request, "Tournament updated successfully.")
        return redirect("tournament_detail", pk=tournament.pk)

    if request.method == "POST":
        messages.error(request, "Please correct the errors below.")

    return render(request, "tournaments/tournament_form.html", {
        "form": form,
        "tournament": tournament
    })


@login_required
def tournament_delete(request, pk):
    tournament = get_object_or_404(
        Tournament,
        pk=pk,
        organization__owner=request.user
    )

    if request.method == "POST":
        tournament.delete()
        return redirect("tournament_list")

    return render(request, "tournaments/tournament_confirm_delete.html", {
        "tournament": tournament
    })

@login_required
def tournament_detail(request, pk):
    tournament = get_object_or_404(
        Tournament.objects.select_related("organization", "champion"),
        pk=pk,
        organization__owner=request.user
    )

    matches = tournament.matches.all().order_by("round_number", "match_number")
    registrations = tournament.registrations.select_related("team").all()

    approved_count = registrations.filter(status="approved").count()

    grouped_matches = {}
    for match in matches:
        grouped_matches.setdefault(match.round_number, []).append(match)

    return render(request, "tournaments/tournament_detail.html", {
        "tournament": tournament,
        "registrations": registrations,
        "matches": matches,
        "grouped_matches": grouped_matches,
        "approved_count": approved_count,
    })



@login_required
@require_POST
@transaction.atomic
def generate_bracket(request, pk):
    tournament = get_object_or_404(
        Tournament.objects.select_for_update(),
        pk=pk,
        organization__owner=request.user
    )

    if tournament.format_type != "single_elimination":
        messages.error(request, "Bracket generation is only available for single elimination tournaments.")
        return redirect("tournament_detail", pk=tournament.id)

    if tournament.matches.exists():
        messages.error(request, "Bracket has already been generated for this tournament.")
        return redirect("tournament_detail", pk=tournament.id)

    registrations = (
        tournament.registrations
        .filter(status="approved")
        .select_related("team")
        .order_by("created_at", "id")
    )
    teams = [r.team for r in registrations]

    if len(teams) < 2:
        messages.error(request, "At least 2 approved teams are required to generate a bracket.")
        return redirect("tournament_detail", pk=tournament.id)

    team_count = len(teams)
    total_rounds = math.ceil(math.log2(team_count))
    bracket_size = 2 ** total_rounds

    all_matches_to_create = []
    for round_number in range(1, total_rounds + 1):
        match_count = bracket_size // (2 ** round_number)
        for match_number in range(1, match_count + 1):
            all_matches_to_create.append(
                Match(
                    tournament=tournament,
                    round_number=round_number,
                    match_number=match_number,
                )
            )

    created_matches = Match.objects.bulk_create(all_matches_to_create)

    all_round_matches = {}
    for match in created_matches:
        all_round_matches.setdefault(match.round_number, []).append(match)
    for round_number in all_round_matches:
        all_round_matches[round_number].sort(key=lambda m: m.match_number)

    matches_to_update = []
    for round_number in range(1, total_rounds):
        current_round = all_round_matches[round_number]
        next_round = all_round_matches[round_number + 1]
        for index, match in enumerate(current_round):
            match.next_match = next_round[index // 2]
            matches_to_update.append(match)
    Match.objects.bulk_update(matches_to_update, ["next_match"])

    slots = [None] * bracket_size
    positions = list(range(bracket_size))
    random.shuffle(positions)
    for i, team in enumerate(teams):
        slots[positions[i]] = team

    first_round_matches = all_round_matches[1]
    first_round_to_update = []
    for i, match in enumerate(first_round_matches):
        match.team1 = slots[i * 2]
        match.team2 = slots[i * 2 + 1]
        if match.team1 is None and match.team2 is None:
            match.status = "completed"
        first_round_to_update.append(match)
    Match.objects.bulk_update(first_round_to_update, ["team1", "team2", "status"])

    bye_advances = []
    for match in first_round_to_update:
        if match.team1 is not None and match.team2 is None:
            match.winner = match.team1
            match.status = "completed"
            bye_advances.append(match)
        elif match.team2 is not None and match.team1 is None:
            match.winner = match.team2
            match.status = "completed"
            bye_advances.append(match)

    if bye_advances:
        Match.objects.bulk_update(bye_advances, ["winner", "status"])
        next_round_updates = []
        for match in bye_advances:
            if match.next_match:
                idx = first_round_to_update.index(match)
                next_m = all_round_matches[2][idx // 2]
                if next_m.team1 is None:
                    next_m.team1 = match.winner
                else:
                    next_m.team2 = match.winner
                if next_m not in next_round_updates:
                    next_round_updates.append(next_m)
        if next_round_updates:
            Match.objects.bulk_update(next_round_updates, ["team1", "team2"])

    tournament.status = "published"
    tournament.champion = None
    tournament.save(update_fields=["status", "champion"])

    messages.success(request, "Bracket generated successfully.")
    return redirect("tournament_detail", pk=tournament.id)



@login_required
@require_POST
@transaction.atomic
def report_match_result(request, match_id):
    match = get_object_or_404(
        Match.objects.select_for_update().select_related(
            "tournament", "next_match", "team1", "team2"
        ),
        pk=match_id,
        tournament__organization__owner=request.user,
    )

    tournament = match.tournament

    if match.status == "completed":
        messages.error(request, "This match result has already been reported.")
        return redirect("tournament_detail", pk=tournament.id)

    if not match.team1 or not match.team2:
        messages.error(request, "This match is not ready yet.")
        return redirect("tournament_detail", pk=tournament.id)

    winner_id = request.POST.get("winner")

    if str(match.team1_id) == winner_id:
        winner = match.team1
    elif str(match.team2_id) == winner_id:
        winner = match.team2
    else:
        messages.error(request, "Invalid winner selected.")
        return redirect("tournament_detail", pk=tournament.id)

    match.winner = winner
    match.status = "completed"
    match.save(update_fields=["winner", "status"])

    if match.next_match:
        next_match = Match.objects.select_for_update().get(pk=match.next_match.pk)

        if next_match.team1 is None:
            next_match.team1 = winner
            next_match.save(update_fields=["team1"])
        elif next_match.team2 is None:
            next_match.team2 = winner
            next_match.save(update_fields=["team2"])
        else:
            messages.error(request, "Next match already has two teams assigned.")
            return redirect("tournament_detail", pk=tournament.id)

        if tournament.status in ["draft", "published"]:
            tournament.status = "ongoing"
            tournament.champion = None
            tournament.save(update_fields=["status", "champion"])
    else:
        tournament.status = "completed"
        tournament.champion = winner
        tournament.save(update_fields=["status", "champion"])

    final_match = (
        Match.objects.select_for_update()
        .filter(tournament=tournament)
        .order_by("-round_number", "-match_number")
        .first()
    )

    if final_match and final_match.winner:
        tournament.status = "completed"
        tournament.champion = final_match.winner
        tournament.save(update_fields=["status", "champion"])

    messages.success(request, "Match result reported successfully.")
    return redirect("tournament_detail", pk=tournament.id)




@login_required
@require_POST
def toggle_registration(request, pk):
    tournament = get_object_or_404(
        Tournament,
        pk=pk,
        organization__owner=request.user
    )

    if tournament.matches.exists():
        messages.error(request, "Cannot change registration status after bracket has been generated.")
        return redirect("tournament_detail", pk=tournament.pk)

    tournament.registration_open = not tournament.registration_open
    tournament.save(update_fields=["registration_open"])

    state = "opened" if tournament.registration_open else "closed"
    messages.success(request, f"Registration {state} for {tournament.name}.")
    return redirect("tournament_detail", pk=tournament.pk)
