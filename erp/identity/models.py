"""Identity models.

A custom User is the auth principal. RBAC is implemented with Django's Group/Permission system
(a Group == a role, e.g. "Accountant", "Branch Manager"); endpoints enforce roles via the DRF
permission classes in ``permissions.py``. TOTP 2FA fields live on the user; the verification flow
is in ``services.py``.
"""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # Email is the primary credential; username kept for admin compatibility.
    email = models.EmailField(unique=True)

    # Per-branch scoping. Null for org-wide roles (e.g. System Admin).
    branch = models.ForeignKey(
        "core.Branch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )

    # TOTP 2FA.
    is_2fa_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=64, blank=True, default="")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "identity_user"

    def __str__(self) -> str:  # pragma: no cover
        return self.email or self.username

    @property
    def roles(self) -> list[str]:
        """Role names (Django groups) assigned to this user."""
        return list(self.groups.values_list("name", flat=True))


# --- Personalization ---------------------------------------------------------------------------
#
# Two additive tables back the per-user Settings experience. Nothing here touches the auth/RBAC
# path: an absent ``UserPreferences`` row simply means "all product defaults", and personal values
# that are left blank fall back to the single ``OrgPreferences`` row (admin-set org defaults). The
# frontend applies these as <html data-*> attributes (theme/accent/density/...), so they are pure
# presentation and never gate behaviour.

# Fields that may be blank on a user to mean "inherit the org default".
THEME_CHOICES = [("system", "System"), ("light", "Light"), ("dark", "Dark")]
ACCENT_CHOICES = [
    ("blue", "Blue"),
    ("black", "Black"),
    ("green", "Green"),
    ("purple", "Purple"),
    ("orange", "Orange"),
    ("red", "Red"),
]
LANGUAGE_CHOICES = [("ar", "Arabic"), ("en", "English")]
DENSITY_CHOICES = [("comfortable", "Comfortable"), ("compact", "Compact")]
FONT_SIZE_CHOICES = [("small", "Small"), ("default", "Default"), ("large", "Large")]
SIDEBAR_CHOICES = [("expanded", "Expanded"), ("compact", "Compact")]
DATE_FORMAT_CHOICES = [("iso", "2026-06-20"), ("dmy", "20/06/2026"), ("mdy", "06/20/2026")]
TIME_FORMAT_CHOICES = [("24h", "24-hour"), ("12h", "12-hour")]
DIGEST_CHOICES = [("off", "Off"), ("daily", "Daily"), ("weekly", "Weekly")]


class UserPreferences(models.Model):
    """Per-user personalization. One row per user (created on first access)."""

    user = models.OneToOneField(
        "identity.User", on_delete=models.CASCADE, related_name="preferences"
    )

    # Profile (photo upload deferred — the UI shows an initials avatar for now).
    display_name = models.CharField(max_length=120, blank=True, default="")
    job_title = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")

    # Locale & formats. preferred_language blank => follow the org default.
    preferred_language = models.CharField(
        max_length=2, choices=LANGUAGE_CHOICES, blank=True, default=""
    )
    time_zone = models.CharField(max_length=64, blank=True, default="Africa/Cairo")
    date_format = models.CharField(max_length=8, choices=DATE_FORMAT_CHOICES, default="iso")
    time_format = models.CharField(max_length=4, choices=TIME_FORMAT_CHOICES, default="24h")

    # Appearance. theme/accent blank => follow the org default.
    theme = models.CharField(max_length=8, choices=THEME_CHOICES, blank=True, default="")
    accent_color = models.CharField(max_length=8, choices=ACCENT_CHOICES, blank=True, default="")
    sidebar_style = models.CharField(max_length=10, choices=SIDEBAR_CHOICES, default="expanded")
    density = models.CharField(max_length=12, choices=DENSITY_CHOICES, default="comfortable")
    font_size = models.CharField(max_length=8, choices=FONT_SIZE_CHOICES, default="default")

    # Accessibility.
    high_contrast = models.BooleanField(default=False)
    reduced_motion = models.BooleanField(default=False)
    keyboard_nav = models.BooleanField(default=False)

    # Notifications.
    notif_email = models.BooleanField(default=True)
    notif_inapp = models.BooleanField(default=True)
    notif_sound = models.BooleanField(default=False)
    notif_desktop = models.BooleanField(default=False)
    digest_frequency = models.CharField(max_length=8, choices=DIGEST_CHOICES, default="off")

    # Workspace. default_landing blank => follow the org default (then "/").
    default_landing = models.CharField(max_length=120, blank=True, default="")
    dashboard_layout = models.JSONField(default=dict, blank=True)  # {order:[], hidden:[]}
    favorites = models.JSONField(default=list, blank=True)  # [{label, to}]

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_user_preferences"
        verbose_name_plural = "user preferences"

    def __str__(self) -> str:  # pragma: no cover
        return f"preferences<{self.user_id}>"


class OrgPreferences(models.Model):
    """Organization-wide defaults (a single row, pk=1). System-Admin editable.

    Users inherit these wherever their personal value is blank. Personal values always win.
    """

    default_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default="ar")
    default_theme = models.CharField(max_length=8, choices=THEME_CHOICES, default="system")
    default_accent = models.CharField(max_length=8, choices=ACCENT_CHOICES, default="blue")
    default_landing = models.CharField(max_length=120, blank=True, default="")
    company_name = models.CharField(max_length=160, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_org_preferences"
        verbose_name_plural = "org preferences"

    def __str__(self) -> str:  # pragma: no cover
        return "org preferences"
