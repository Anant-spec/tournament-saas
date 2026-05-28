from django.urls import path
from . import views

urlpatterns = [
    path("", views.organization_list, name="organization_list"),
    path("create/", views.organization_create, name="organization_create"),
    path("update/<uuid:pk>/", views.organization_update, name="organization_update"),
    path("delete/<uuid:pk>/", views.organization_delete, name="organization_delete"),
]