"""Monitoring routes."""
from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("health", views.health, name="health"),
    path("system-check", views.system_check, name="system-check"),
]
