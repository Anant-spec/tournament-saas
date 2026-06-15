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

        # Disable round_robin — not yet implemented
        format_field = self.fields["format_type"]
        format_field.widget = forms.Select(
            choices=Tournament.FORMAT_CHOICES,
            attrs=format_field.widget.attrs
        )
        format_field.widget.option_attrs = {"round_robin": {"disabled": True}}

        if self.instance and self.instance.pk and self.instance.matches.exists():
            self.fields["organization"].disabled = True
            self.fields["format_type"].disabled = True
            self.fields["organization"].required = False
            self.fields["format_type"].required = False

    def clean_format_type(self):
        value = self.cleaned_data.get("format_type")
        # Belt-and-suspenders: block round_robin even if someone bypasses the UI
        if value == "round_robin":
            raise forms.ValidationError("Round Robin is not available yet. Please select Single Elimination.")
        if self.instance and self.instance.pk and self.instance.matches.exists():
            return self.instance.format_type
        return value

    def clean_organization(self):
        if self.instance and self.instance.pk and self.instance.matches.exists():
            return self.instance.organization
        return self.cleaned_data.get("organization")