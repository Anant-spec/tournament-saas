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
from collections import defaultdict

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


def _build_stats(matches, registrations):
    """
    Compute tournament stats from a queryset of matches.
    Returns a dict ready to be passed to the template context.
    """
    all_matches = list(matches)

    real_matches = [m for m in all_matches if m.team1_id or m.team2_id]
    two_team_matches = [m for m in real_matches if m.team1_id and m.team2_id]
    completed = [m for m in two_team_matches if m.status == "completed"]
    pending   = [m for m in two_team_matches if m.status == "pending"]

    total_real    = len(two_team_matches)
    total_done    = len(completed)
    total_pending = len(pending)
    progress_pct  = round((total_done / total_real * 100) if total_real else 0)

    round_stats = defaultdict(lambda: {"total": 0, "done": 0})
    for m in two_team_matches:
        round_stats[m.round_number]["total"] += 1
        if m.status == "completed":
            round_stats[m.round_number]["done"] += 1
    round_stats = [
        {
            "round": rn,
            "total": v["total"],
            "done":  v["done"],
            "pct":   round(v["done"] / v["total"] * 100) if v["total"] else 0,
        }
        for rn, v in sorted(round_stats.items())
    ]

    wins   = defaultdict(int)
    losses = defaultdict(int)
    appearances = defaultdict(int)
    team_names  = {}

    for m in completed:
        if m.team1:
            team_names[m.team1_id] = m.team1.name
            appearances[m.team1_id] += 1
        if m.team2:
            team_names[m.team2_id] = m.team2.name
            appearances[m.team2_id] += 1
        if m.winner_id:
            wins[m.winner_id] += 1
            loser_id = m.team1_id if m.winner_id == m.team2_id else m.team2_id
            if loser_id:
                losses[loser_id] += 1

    for reg in registrations:
        if reg.team_id not in team_names:
            team_names[reg.team_id] = reg.team.name

    team_stats = []
    for tid, name in team_names.items():
        w  = wins.get(tid, 0)
        l  = losses.get(tid, 0)
        played = w + l
        rate = round(w / played * 100) if played else None
        team_stats.append({
            "name":    name,
            "wins":    w,
            "losses":  l,
            "played":  played,
            "win_pct": rate,
        })

    team_stats.sort(key=lambda t: (-t["wins"], t["name"]))

    return {
        "stats_total":      total_real,
        "stats_done":       total_done,
        "stats_pending":    total_pending,
        "stats_progress":   progress_pct,
        "stats_rounds":     round_stats,
        "stats_teams":      team_stats,
        "stats_has_data":   total_real > 0,
    }


@login_required
def tournament_detail(request, pk):
    tournament = get_object_or_404(
        Tournament.objects.select_related("organization", "champion"),
        pk=pk,
        organization__owner=request.user
    )

    matches = (
        tournament.matches
        .select_related("team1", "team2", "winner", "next_match")
        .prefetch_related(
            "team1__players",
            "team2__players",
        )
        .order_by("round_number", "match_number")
    )

    registrations = tournament.registrations.select_related("team").all()
    approved_count = registrations.filter(status="approved").count()

    grouped_matches = {}
    for match in matches:
        grouped_matches.setdefault(match.round_number, []).append(match)

    stats = _build_stats(matches, registrations)

    return render(request, "tournaments/tournament_detail.html", {
        "tournament":      tournament,
        "registrations":   registrations,
        "matches":         matches,
        "grouped_matches": grouped_matches,
        "approved_count":  approved_count,
        **stats,
    })


@login_required
@require_POST
@transaction.atomic
def reset_bracket(request, pk):
    tournament = get_object_or_404(
        Tournament.objects.select_for_update(),
        pk=pk,
        organization__owner=request.user
    )

    confirm_name = request.POST.get("confirm_name", "").strip()
    if confirm_name != tournament.name:
        messages.error(request, "Tournament name did not match. Bracket reset cancelled.")
        return redirect("tournament_detail", pk=tournament.pk)

    if not tournament.matches.exists():
        messages.info(request, "No bracket to reset.")
        return redirect("tournament_detail", pk=tournament.pk)

    deleted_count, _ = tournament.matches.all().delete()

    tournament.status = "draft"
    tournament.champion = None
    tournament.save(update_fields=["status", "champion"])

    messages.success(
        request,
        f"Bracket reset. {deleted_count} match{'es' if deleted_count != 1 else ''} deleted. "
        f"Approved teams remain approved — regenerate when ready."
    )
    return redirect("tournament_detail", pk=tournament.pk)


@login_required
@require_POST
@transaction.atomic
def generate_bracket(request, pk):
    """
    Single-elimination bracket using the industry-standard power-of-2 bye system.

    Given n teams:
      - bracket_size = next power of 2 >= n  (e.g. 5 teams -> 8 slots)
      - byes_needed  = bracket_size - n       (e.g. 8 - 5 = 3 byes)
      - The first `byes_needed` teams skip round 1 and enter directly at round 2.
      - The remaining `n - byes_needed` teams play real matches in round 1.
      - From round 2 onwards the bracket is a perfect power-of-2 — no cascading
        odd-team issues ever occur.

    This matches the format used by Challonge, Battlefy, and all major esports
    platforms (ESL, BLAST, etc.).
    """
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

    random.shuffle(teams)

    # --- Power-of-2 bracket sizing ---
    team_count   = len(teams)
    total_rounds = math.ceil(math.log2(team_count))
    bracket_size = 2 ** total_rounds          # next power of 2 >= team_count
    byes_needed  = bracket_size - team_count  # teams that skip round 1

    # Separate bye teams (skip round 1) from playing teams (compete in round 1)
    bye_teams     = teams[:byes_needed]        # enter at round 2
    playing_teams = teams[byes_needed:]        # play in round 1
    # len(playing_teams) is always even: bracket_size - byes = 2*team_count - bracket_size

    # --- Create all match slots for every round ---
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

    # Build lookup: {round_number: [match, ...]} sorted by match_number
    round_map = {}
    for m in created_matches:
        round_map.setdefault(m.round_number, []).append(m)
    for r in round_map:
        round_map[r].sort(key=lambda m: m.match_number)

    # --- Wire next_match pointers (round N -> round N+1) ---
    pointer_updates = []
    for rn in range(1, total_rounds):
        for i, match in enumerate(round_map[rn]):
            match.next_match = round_map[rn + 1][i // 2]
            pointer_updates.append(match)
    if pointer_updates:
        Match.objects.bulk_update(pointer_updates, ["next_match"])

    # --- Assign playing teams to round 1 matches ---
    # playing_teams is always even-length so every match gets exactly 2 teams.
    r1_updates = []
    for i, match in enumerate(round_map[1]):
        match.team1 = playing_teams[i * 2]
        match.team2 = playing_teams[i * 2 + 1]
        r1_updates.append(match)
    Match.objects.bulk_update(r1_updates, ["team1", "team2"])

    # --- Place bye teams directly into round 2 slots ---
    # Bye teams occupy the LAST slots in round 2 (after the round-1 feeders).
    # Round 2 has bracket_size/4 matches.
    # The first (len(playing_teams)//2) slots are fed by round-1 winners.
    # The remaining `byes_needed` slots get bye teams, packed in pairs.
    r2_updates = {}
    r2_matches = round_map.get(2, [])
    r1_feeder_count = len(playing_teams) // 2  # number of round-2 slots fed by round 1

    for i, team in enumerate(bye_teams):
        slot_index = r1_feeder_count + (i // 2)  # which round-2 match
        if slot_index < len(r2_matches):
            target = r2_matches[slot_index]
            if target.team1 is None:
                target.team1 = team
            else:
                target.team2 = team
            r2_updates[target.pk] = target

    if r2_updates:
        Match.objects.bulk_update(r2_updates.values(), ["team1", "team2"])

    tournament.status = "published"
    tournament.champion = None
    tournament.save(update_fields=["status", "champion"])

    messages.success(
        request,
        f"Bracket generated: {len(playing_teams) // 2} round-1 match"
        f"{'es' if len(playing_teams) // 2 != 1 else ''}, "
        f"{byes_needed} team{'s' if byes_needed != 1 else ''} with a bye to round 2."
        if byes_needed else "Bracket generated successfully."
    )
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
