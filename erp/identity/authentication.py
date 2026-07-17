"""API key authentication — ``Authorization: Api-Key <secret>``.

The secret (``ck_<prefix>_<random>``) is never stored — only its SHA-256 hash. On success the
key's dedicated principal (never a human user, see ``models.ApiKey``) becomes ``request.user``, so
it carries the bound role through the exact same RBAC/scoping/audit path a human login uses.
"""
from __future__ import annotations

import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.throttling import UserRateThrottle

AUTH_KEYWORD = b"api-key"


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class ApiKeyAuthentication(BaseAuthentication):
    """Authenticates ``Authorization: Api-Key <secret>``; falls through (returns None) for any
    other scheme so it can sit alongside JWTAuthentication without interfering with it."""

    keyword = "Api-Key"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != AUTH_KEYWORD:
            return None
        if len(auth) != 2:
            raise AuthenticationFailed("Malformed Api-Key header")
        return self._authenticate_secret(auth[1].decode("utf-8"))

    def _authenticate_secret(self, secret: str):
        from .models import ApiKey

        try:
            api_key = ApiKey.objects.select_related("principal").get(
                hashed_key=hash_secret(secret)
            )
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")
        if not api_key.is_active:
            raise AuthenticationFailed("API key revoked")
        if api_key.expires_at and api_key.expires_at <= timezone.now():
            raise AuthenticationFailed("API key expired")
        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        return (api_key.principal, api_key)

    def authenticate_header(self, request):
        return self.keyword


class ApiKeyRateThrottle(UserRateThrottle):
    """Separate throttle scope for key traffic (env-tunable ``DRF_THROTTLE_API_KEY``).

    Every request runs through every ``DEFAULT_THROTTLE_CLASSES`` entry; returning ``None`` from
    ``get_cache_key`` opts a request out of *this* throttle only, so human (JWT) traffic keeps
    using the plain ``UserRateThrottle`` scope untouched.
    """

    scope = "api_key"

    def get_cache_key(self, request, view):
        from .models import ApiKey

        if not isinstance(request.auth, ApiKey):
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.auth.pk}
