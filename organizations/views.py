from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Organization
from .forms import OrganizationForm

@login_required
def organization_list(request):
    organizations = Organization.objects.filter(
        owner=request.user
    ).prefetch_related("tournaments")  # ADD THIS
    return render(request, "organizations/organization_list.html", {
        "organizations": organizations
    })

@login_required
def organization_create(request):
    form = OrganizationForm(request.POST or None)

    if form.is_valid():
        organization = form.save(commit=False)
        organization.owner = request.user
        organization.save()
        return redirect("organization_list")

    return render(request, "organizations/organization_form.html", {
        "form": form
    })

@login_required
def organization_update(request, pk):
    organization = get_object_or_404(Organization, pk=pk, owner=request.user)
    form = OrganizationForm(request.POST or None, instance=organization)

    if form.is_valid():
        form.save()
        return redirect("organization_list")

    return render(request, "organizations/organization_form.html", {
        "form": form
    })

@login_required
def organization_delete(request, pk):
    organization = get_object_or_404(Organization, pk=pk, owner=request.user)

    if request.method == "POST":
        organization.delete()
        return redirect("organization_list")

    return render(request, "organizations/organization_confirm_delete.html", {
        "organization": organization
    })


@login_required
def organization_detail(request, pk):
    organization = get_object_or_404(Organization, pk=pk, owner=request.user)
    return render(request, "organizations/organization_detail.html", {
        "organization": organization
    })