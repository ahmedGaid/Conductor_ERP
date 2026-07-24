"""WorkSession API routes."""
from django.urls import path

from . import views

app_name = "worksessions"

urlpatterns = [
    path("", views.DraftListCreateView.as_view(), name="draft-list-create"),
    path("active", views.ActiveDraftView.as_view(), name="draft-active"),
    path("<uuid:pk>/discard", views.DiscardDraftView.as_view(), name="draft-discard"),
    path("<uuid:pk>/complete", views.CompleteDraftView.as_view(), name="draft-complete"),
]
