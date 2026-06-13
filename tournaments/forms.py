from django import forms
from .models import Tournament
from organizations.models import Organization

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "organization",
            "name",
            "game_title",
            "format_type",
            "start_date",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["organization"].queryset = self.fields["organization"].queryset.filter(owner=user)

        if self.instance and self.instance.pk and self.instance.matches.exists():
            self.fields["organization"].disabled = True
            self.fields["format_type"].disabled = True
            self.fields["organization"].required = False
            self.fields["format_type"].required = False

    def clean_organization(self):
        if self.instance and self.instance.pk and self.instance.matches.exists():
            return self.instance.organization
        return self.cleaned_data.get("organization")

    def clean_format_type(self):
        if self.instance and self.instance.pk and self.instance.matches.exists():
            return self.instance.format_type
        return self.cleaned_data.get("format_type")