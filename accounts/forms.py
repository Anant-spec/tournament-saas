from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=255, required=False)

    class Meta:
        model = User
        fields = ("email", "full_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.full_name = self.cleaned_data.get("full_name", "")
        if commit:
            user.save()
        return user