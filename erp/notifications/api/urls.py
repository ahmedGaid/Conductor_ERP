"""Notifications API routes."""
from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("notifications", views.NotificationListView.as_view(), name="notification-list"),
    # In-app inbox — specific paths before the generic <uuid>/resend so they win the match.
    path("notifications/inbox", views.InboxListView.as_view(), name="inbox-list"),
    path("notifications/inbox/read-all", views.InboxMarkAllReadView.as_view(),
         name="inbox-mark-all-read"),
    path("notifications/inbox/<uuid:note_id>/read", views.InboxMarkReadView.as_view(),
         name="inbox-mark-read"),
    path("notifications/<uuid:note_id>/resend", views.NotificationResendView.as_view(),
         name="notification-resend"),
]
