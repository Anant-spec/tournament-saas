from django import forms
from .models import Team

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["tournament", "name", "captain_name", "captain_email"]