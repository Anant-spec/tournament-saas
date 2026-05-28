from django import forms
from .models import Tournament
from organizations.models import Organization

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "organization",
            "name",
            "slug",
            "game_title",
            "format_type",
            "status",
            "registration_open",
            "start_date",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user is not None:
            self.fields["organization"].queryset = Organization.objects.filter(owner=self.user)

    def clean_organization(self):
        organization = self.cleaned_data["organization"]
        if self.user is not None and organization.owner != self.user:
            raise forms.ValidationError("Invalid organization.")
        return organization