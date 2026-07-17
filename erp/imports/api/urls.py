"""Smart Import Engine API routes."""
from django.urls import path

from . import views

app_name = "imports"

urlpatterns = [
    path("upload", views.UploadView.as_view(), name="upload"),
    path("profiles", views.ProfilesView.as_view(), name="profile-list"),
    path("profiles/<uuid:pk>", views.ProfileDetailView.as_view(), name="profile-detail"),
    path("", views.BatchListView.as_view(), name="batch-list"),
    path("<uuid:pk>", views.BatchDetailView.as_view(), name="batch-detail"),
    path("<uuid:pk>/mapping", views.MappingView.as_view(), name="batch-mapping"),
    path("<uuid:pk>/rows", views.BatchRowsView.as_view(), name="batch-rows"),
    path("<uuid:pk>/rows/<int:row_number>", views.RowDetailView.as_view(), name="batch-row-detail"),
    path("<uuid:pk>/autofix", views.AutofixPreviewView.as_view(), name="batch-autofix"),
    path("<uuid:pk>/autofix/apply", views.AutofixApplyView.as_view(), name="batch-autofix-apply"),
    path("<uuid:pk>/creation-plan", views.CreationPlanView.as_view(), name="batch-creation-plan"),
    path("<uuid:pk>/execute", views.ExecuteView.as_view(), name="batch-execute"),
    path("<uuid:pk>/pause", views.PauseView.as_view(), name="batch-pause"),
    path("<uuid:pk>/resume", views.ResumeView.as_view(), name="batch-resume"),
    path("<uuid:pk>/cancel", views.CancelView.as_view(), name="batch-cancel"),
    path("<uuid:pk>/rollback", views.RollbackView.as_view(), name="batch-rollback"),
    path("<uuid:pk>/report", views.ReportView.as_view(), name="batch-report"),
]
