from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Team, Registration
from .forms import TeamForm

@login_required
def team_list(request):
    teams = Team.objects.filter(
        tournament__organization__owner=request.user
    )
    return render(request, "registrations/team_list.html", {
        "teams": teams
    })

@login_required
def team_create(request):
    form = TeamForm(request.POST or None)

    form.fields["tournament"].queryset = form.fields["tournament"].queryset.filter(
        organization__owner=request.user
    )

    if form.is_valid():
        team = form.save()

        Registration.objects.create(
            tournament=team.tournament,
            team=team,
            status="pending"
        )

        return redirect("team_list")

    return render(request, "registrations/team_form.html", {
        "form": form
    })