from django.urls import path

from .views import AssistantStatusView, ExtractDocumentView

urlpatterns = [
    path("status", AssistantStatusView.as_view(), name="assistant-status"),
    path("extract-document", ExtractDocumentView.as_view(), name="assistant-extract-document"),
]
