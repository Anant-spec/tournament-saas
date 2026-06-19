from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = "email"
    # username is auto-set to email in SignupForm — no need to prompt for it separately
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
