from django.urls import path

from .views import AskView, AssistantStatusView, ExtractDocumentView

urlpatterns = [
    path("status", AssistantStatusView.as_view(), name="assistant-status"),
    path("extract-document", ExtractDocumentView.as_view(), name="assistant-extract-document"),
    path("ask", AskView.as_view(), name="assistant-ask"),
]
