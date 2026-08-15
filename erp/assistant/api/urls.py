from django.urls import path

from .memory import MemoryDetailView, MemoryProposalView, MemoryView
from .ops import OpsSummaryView, OpsTracesView
from .usage import UsageView
from .views import (
    ActionExecuteView,
    AskView,
    AssistantStatusView,
    AttachmentsView,
    ChatCancelView,
    ChatRetryView,
    ChatStreamView,
    ClarifyAnswerView,
    ChatView,
    ConversationDetailView,
    ConversationsView,
    DetourResumeView,
    ExtractDocumentView,
    ImportExecuteView,
    ImportInspectView,
    ImportPreviewView,
    KnowledgeDetailView,
    KnowledgeView,
    SimulateView,
)

urlpatterns = [
    path("status", AssistantStatusView.as_view(), name="assistant-status"),
    path("extract-document", ExtractDocumentView.as_view(), name="assistant-extract-document"),
    path("attachments", AttachmentsView.as_view(), name="assistant-attachments"),
    path("ask", AskView.as_view(), name="assistant-ask"),
    path("chat", ChatView.as_view(), name="assistant-chat"),
    path("actions/execute", ActionExecuteView.as_view(), name="assistant-action-execute"),
    path("simulate", SimulateView.as_view(), name="assistant-simulate"),
    path("imports/inspect", ImportInspectView.as_view(), name="assistant-import-inspect"),
    path("imports/preview", ImportPreviewView.as_view(), name="assistant-import-preview"),
    path("imports/execute", ImportExecuteView.as_view(), name="assistant-import-execute"),
    path("clarify/answer", ClarifyAnswerView.as_view(), name="assistant-clarify-answer"),
    path("detours/resume", DetourResumeView.as_view(), name="assistant-detour-resume"),
    path("conversations", ConversationsView.as_view(), name="assistant-conversations"),
    path("conversations/<int:pk>", ConversationDetailView.as_view(), name="assistant-conversation"),
    path("conversations/<int:pk>/stream", ChatStreamView.as_view(), name="assistant-conversation-stream"),
    path("conversations/<int:pk>/retry-turn", ChatRetryView.as_view(), name="assistant-conversation-retry"),
    path("conversations/<int:pk>/cancel-stream", ChatCancelView.as_view(), name="assistant-conversation-cancel"),
    path("knowledge", KnowledgeView.as_view(), name="assistant-knowledge"),
    path("knowledge/<int:pk>", KnowledgeDetailView.as_view(), name="assistant-knowledge-detail"),
    path("memory", MemoryView.as_view(), name="assistant-memory"),
    path("memory/proposals", MemoryProposalView.as_view(), name="assistant-memory-proposals"),
    path("memory/<int:pk>", MemoryDetailView.as_view(), name="assistant-memory-detail"),
    path("ops/summary", OpsSummaryView.as_view(), name="assistant-ops-summary"),
    path("ops/traces", OpsTracesView.as_view(), name="assistant-ops-traces"),
    path("usage", UsageView.as_view(), name="assistant-usage"),
]
