from django.contrib import admin
from django.urls import path, include
from accounts.views import signup
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/signup/", signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
    path("organizations/", include("organizations.urls")),
    path("tournaments/", include("tournaments.urls")),
    path("registrations/", include("registrations.urls")),
    path("api/", include("tournaments.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]