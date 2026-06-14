from django import forms
from .models import Team, Player

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["tournament", "name", "captain_name", "captain_email"]





class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["full_name", "in_game_name", "game_uid", "role"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "in_game_name": forms.TextInput(attrs={"placeholder": "In-game username"}),
            "game_uid": forms.TextInput(attrs={"placeholder": "Game UID (optional)"}),
        }