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