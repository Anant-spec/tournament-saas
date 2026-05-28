from django.urls import path
from . import views

urlpatterns = [
    path("", views.tournament_list, name="tournament_list"),
    path("create/", views.tournament_create, name="tournament_create"),
    path("<uuid:pk>/edit/", views.tournament_edit, name="tournament_edit"),
    path("<uuid:pk>/delete/", views.tournament_delete, name="tournament_delete"),
    path("<uuid:pk>/", views.tournament_detail, name="tournament_detail"),
    path("<uuid:pk>/generate-bracket/", views.generate_bracket, name="generate_bracket"),
    path("matches/<uuid:match_id>/report/", views.report_match_result, name="report_match_result"),
]