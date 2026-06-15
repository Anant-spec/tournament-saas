from django import forms
from .models import Team, Player

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["tournament", "name", "captain_name", "captain_email"]


class PublicTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "captain_name", "captain_email"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Team Nexus"}),
            "captain_name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "captain_email": forms.EmailInput(attrs={"placeholder": "captain@email.com"}),
        }


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["full_name", "in_game_name", "game_uid", "role"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "in_game_name": forms.TextInput(attrs={"placeholder": "In-game username"}),
            "game_uid": forms.TextInput(attrs={"placeholder": "Game UID (optional)"}),
        }