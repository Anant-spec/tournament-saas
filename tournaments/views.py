import math
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Tournament, Match
from organizations.models import Organization
from .forms import TournamentForm
from registrations.models import Team
from django.views.decorators.http import require_POST

@login_required
def tournament_list(request):
    tournaments = Tournament.objects.filter(
        organization__owner=request.user
    )
    return render(request, "tournaments/tournament_list.html", {
        "tournaments": tournaments
    })

@login_required
def tournament_create(request):
    form = TournamentForm(request.POST or None, user=request.user)

    if form.is_valid():
        tournament = form.save()
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
        return redirect("tournament_list")

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
        Tournament,
        pk=pk,
        organization__owner=request.user
    )
    matches = tournament.matches.all().order_by("round_number", "match_number")

    rounds = {}
    for match in matches:
        rounds.setdefault(match.round_number, []).append(match)

    return render(request, "tournaments/tournament_detail.html", {
        "tournament": tournament,
        "rounds": rounds
    })

@login_required
def generate_bracket(request, pk):
    tournament = get_object_or_404(
        Tournament,
        pk=pk,
        organization__owner=request.user
    )

    if tournament.format_type != "single_elimination":
        return redirect("tournament_detail", pk=tournament.id)

    teams = list(tournament.teams.all().order_by("created_at"))

    if len(teams) < 2:
        return redirect("tournament_detail", pk=tournament.id)

    tournament.matches.all().delete()
    tournament.champion = None
    tournament.status = "draft"
    tournament.save(update_fields=["champion", "status"])

    team_count = len(teams)
    total_rounds = math.ceil(math.log2(team_count))
    bracket_size = 2 ** total_rounds

    all_round_matches = {}

    for round_number in range(1, total_rounds + 1):
        match_count = bracket_size // (2 ** round_number)
        matches = []

        for match_number in range(1, match_count + 1):
            match = Match.objects.create(
                tournament=tournament,
                round_number=round_number,
                match_number=match_number
            )
            matches.append(match)

        all_round_matches[round_number] = matches

    for round_number in range(1, total_rounds):
        current_round = all_round_matches[round_number]
        next_round = all_round_matches[round_number + 1]

        for index, match in enumerate(current_round):
            match.next_match = next_round[index // 2]
            match.save(update_fields=["next_match"])

    slots = teams + [None] * (bracket_size - team_count)

    first_round_matches = all_round_matches[1]

    for i, match in enumerate(first_round_matches):
        team1 = slots[i * 2]
        team2 = slots[i * 2 + 1]

        match.team1 = team1
        match.team2 = team2

        if team1 and not team2:
            match.winner = team1
            match.status = "completed"
        elif team2 and not team1:
            match.winner = team2
            match.status = "completed"

        match.save()

    for match in first_round_matches:
        if match.winner and match.next_match:
            next_match = match.next_match

            if next_match.team1 is None:
                next_match.team1 = match.winner
            elif next_match.team2 is None:
                next_match.team2 = match.winner

            next_match.save()

    return redirect("tournament_detail", pk=tournament.id)

@login_required
def report_match_result(request, match_id):
    match = get_object_or_404(
        Match,
        pk=match_id,
        tournament__organization__owner=request.user
    )

    if request.method == "POST":
        winner_id = request.POST.get("winner")

        if str(match.team1_id) == winner_id:
            winner = match.team1
        elif str(match.team2_id) == winner_id:
            winner = match.team2
        else:
            return redirect("tournament_detail", pk=match.tournament.id)

        match.winner = winner
        match.status = "completed"
        match.save(update_fields=["winner", "status"])

        tournament = match.tournament

        if match.next_match:
            next_match = match.next_match

            if next_match.team1 is None:
                next_match.team1 = winner
            elif next_match.team2 is None:
                next_match.team2 = winner

            next_match.save(update_fields=["team1", "team2"])

            if tournament.status in ["draft", "published"]:
                tournament.status = "ongoing"
                tournament.save(update_fields=["status"])
        else:
            tournament.status = "completed"
            tournament.champion_id = winner.id
            tournament.save(update_fields=["status", "champion_id"])

        return redirect("tournament_detail", pk=tournament.id)

    return redirect("tournament_detail", pk=match.tournament.id)



@login_required
@require_POST
def report_match_result(request, match_id):
    match = get_object_or_404(
        Match,
        pk=match_id,
        tournament__organization__owner=request.user
    )

    winner_id = request.POST.get("winner")

    if str(match.team1_id) == winner_id:
        winner = match.team1
    elif str(match.team2_id) == winner_id:
        winner = match.team2
    else:
        return redirect("tournament_detail", pk=match.tournament.id)

    match.winner = winner
    match.status = "completed"
    match.save(update_fields=["winner", "status"])

    tournament = match.tournament

    if match.next_match:
        next_match = match.next_match

        if next_match.team1 is None:
            next_match.team1 = winner
            next_match.save(update_fields=["team1"])
        elif next_match.team2 is None:
            next_match.team2 = winner
            next_match.save(update_fields=["team2"])

        if tournament.status in ["draft", "published"]:
            tournament.status = "ongoing"
            tournament.save(update_fields=["status"])
    else:
        tournament.status = "completed"
        tournament.champion_id = winner.id
        tournament.save(update_fields=["status", "champion_id"])

    return redirect("tournament_detail", pk=tournament.id)