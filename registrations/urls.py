from django.urls import path
from . import views

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("create/", views.team_create, name="team_create"),
    path("<int:pk>/approve/", views.approve_registration, name="approve_registration"),
    path("<int:pk>/reject/", views.reject_registration, name="reject_registration"),
]