"""Notifications API routes."""
from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("notifications", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/<uuid:note_id>/resend", views.NotificationResendView.as_view(),
         name="notification-resend"),
]
