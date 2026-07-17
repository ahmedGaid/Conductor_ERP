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
    # Outbound webhooks — "events" (static) before "<uuid:subscription_id>" so it wins the match.
    path("notifications/webhooks", views.WebhookSubscriptionListView.as_view(),
         name="webhook-list"),
    path("notifications/webhooks/events", views.WebhookEventCatalogView.as_view(),
         name="webhook-events"),
    path("notifications/webhooks/deliveries/<uuid:delivery_id>/retry",
         views.WebhookDeliveryRetryView.as_view(), name="webhook-delivery-retry"),
    path("notifications/webhooks/<uuid:subscription_id>",
         views.WebhookSubscriptionDetailView.as_view(), name="webhook-detail"),
    path("notifications/webhooks/<uuid:subscription_id>/secret",
         views.WebhookSecretRegenerateView.as_view(), name="webhook-secret"),
    path("notifications/webhooks/<uuid:subscription_id>/deliveries",
         views.WebhookDeliveryListView.as_view(), name="webhook-deliveries"),
]
