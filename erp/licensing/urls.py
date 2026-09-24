"""Licensing API routes."""
from django.urls import path

from . import views

app_name = "licensing"

urlpatterns = [
    path("", views.LicenseView.as_view(), name="license"),
]
