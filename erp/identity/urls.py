"""Identity API routes."""
from django.urls import path

from . import views

app_name = "identity"

urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("token/refresh", views.CookieTokenRefreshView.as_view(), name="token-refresh"),
    path("me", views.MeView.as_view(), name="me"),
    path("2fa/provision", views.Provision2FAView.as_view(), name="2fa-provision"),
    path("2fa/enable", views.Enable2FAView.as_view(), name="2fa-enable"),
    path("sample/finance", views.FinanceSampleView.as_view(), name="sample-finance"),
    path("preferences", views.PreferencesView.as_view(), name="preferences"),
    path("preferences/effective", views.EffectivePreferencesView.as_view(), name="preferences-effective"),
    path("org-preferences", views.OrgPreferencesView.as_view(), name="org-preferences"),
    # Saved views (per-list filter presets)
    path("saved-views", views.SavedViewsView.as_view(), name="saved-views"),
    path("saved-views/<int:pk>", views.SavedViewDetailView.as_view(), name="saved-view-detail"),
    path("saved-views/<int:pk>/default", views.SavedViewDefaultView.as_view(), name="saved-view-default"),
    # User management
    path("users", views.UsersView.as_view(), name="users"),
    path("users/bulk", views.UsersBulkView.as_view(), name="users-bulk"),
    path("users/org-units", views.OrgUnitsView.as_view(), name="users-org-units"),
    path("users/<int:pk>", views.UserDetailView.as_view(), name="user-detail"),
    path("users/<int:pk>/reset-password", views.UserResetPasswordView.as_view(), name="user-reset-password"),
    path("users/<int:pk>/revoke-sessions", views.UserRevokeSessionsView.as_view(), name="user-revoke-sessions"),
    path("users/<int:pk>/sessions/<int:token_id>/revoke", views.UserRevokeSessionView.as_view(), name="user-revoke-session"),
    # Role editor (registry must precede the <name> catch-all)
    path("roles", views.RolesView.as_view(), name="roles"),
    path("roles/registry", views.RoleRegistryView.as_view(), name="roles-registry"),
    path("roles/<str:name>", views.RoleDetailView.as_view(), name="role-detail"),
    path("roles/<str:name>/permission", views.RolePermissionView.as_view(), name="role-permission"),
    path("roles/<str:name>/approval-limit", views.RoleApprovalLimitView.as_view(), name="role-approval-limit"),
    # API keys (integration credentials)
    path("api-keys", views.ApiKeysView.as_view(), name="api-keys"),
    path("api-keys/<int:pk>/revoke", views.ApiKeyRevokeView.as_view(), name="api-key-revoke"),
    path("api-docs", views.ApiDocsView.as_view(), name="api-docs"),
]
