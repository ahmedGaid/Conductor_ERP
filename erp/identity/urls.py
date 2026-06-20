"""Identity API routes."""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "identity"

urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    path("me", views.MeView.as_view(), name="me"),
    path("2fa/provision", views.Provision2FAView.as_view(), name="2fa-provision"),
    path("2fa/enable", views.Enable2FAView.as_view(), name="2fa-enable"),
    path("sample/finance", views.FinanceSampleView.as_view(), name="sample-finance"),
    path("preferences", views.PreferencesView.as_view(), name="preferences"),
    path("preferences/effective", views.EffectivePreferencesView.as_view(), name="preferences-effective"),
    path("org-preferences", views.OrgPreferencesView.as_view(), name="org-preferences"),
]
