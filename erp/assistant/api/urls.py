from django.urls import path

from .views import (
    ActionExecuteView,
    AskView,
    AssistantStatusView,
    AttachmentsView,
    ChatView,
    ConversationDetailView,
    ConversationsView,
    ExtractDocumentView,
    KnowledgeDetailView,
    KnowledgeView,
)

urlpatterns = [
    path("status", AssistantStatusView.as_view(), name="assistant-status"),
    path("extract-document", ExtractDocumentView.as_view(), name="assistant-extract-document"),
    path("attachments", AttachmentsView.as_view(), name="assistant-attachments"),
    path("ask", AskView.as_view(), name="assistant-ask"),
    path("chat", ChatView.as_view(), name="assistant-chat"),
    path("actions/execute", ActionExecuteView.as_view(), name="assistant-action-execute"),
    path("conversations", ConversationsView.as_view(), name="assistant-conversations"),
    path("conversations/<int:pk>", ConversationDetailView.as_view(), name="assistant-conversation"),
    path("knowledge", KnowledgeView.as_view(), name="assistant-knowledge"),
    path("knowledge/<int:pk>", KnowledgeDetailView.as_view(), name="assistant-knowledge-detail"),
]
