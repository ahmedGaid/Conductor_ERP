"""Saved-view services: owner-scoped CRUD for a user's named list filter presets.

Business logic lives here (not in views). Every function is scoped to the owning user, so a saved
view is invisible — and untouchable — to anyone else. Default uniqueness (at most one default per
list) is enforced here, not by a DB constraint, because "unset the old default" is a write.
"""
from __future__ import annotations

from django.db import models

from erp.audit import services as audit
from erp.core.errors import ConflictError, NotFoundError

from .models import SavedView


def list_views(user, list_key: str) -> models.QuerySet[SavedView]:
    """The user's views for one list, name-ordered (defaults never leak across users)."""
    return SavedView.objects.filter(user=user, list_key=list_key)


def _get_owned(user, view_id: int) -> SavedView:
    """Fetch one of the user's own views, or 404 — an unknown id and someone else's id look alike."""
    try:
        return SavedView.objects.get(pk=view_id, user=user)
    except SavedView.DoesNotExist:
        raise NotFoundError("Saved view not found") from None


def create_view(user, list_key: str, name: str, query: str = "", is_default: bool = False) -> SavedView:
    name = name.strip()
    if not name:
        raise ConflictError("Name a view before saving it")
    if SavedView.objects.filter(user=user, list_key=list_key, name=name).exists():
        raise ConflictError("You already have a view with that name")
    view = SavedView.objects.create(
        user=user, list_key=list_key, name=name, query=query, is_default=is_default
    )
    if is_default:
        _clear_other_defaults(user, list_key, keep=view.pk)
    audit.record(
        module="identity", action="create_saved_view", entity_type="SavedView",
        entity_id=view.pk, actor=user, after={"list_key": list_key, "name": name},
    )
    return view


def rename_view(user, view_id: int, name: str) -> SavedView:
    name = name.strip()
    if not name:
        raise ConflictError("Name a view before saving it")
    view = _get_owned(user, view_id)
    clash = SavedView.objects.filter(user=user, list_key=view.list_key, name=name).exclude(pk=view.pk)
    if clash.exists():
        raise ConflictError("You already have a view with that name")
    view.name = name
    view.save(update_fields=["name", "updated_at"])
    audit.record(
        module="identity", action="rename_saved_view", entity_type="SavedView",
        entity_id=view.pk, actor=user, after={"name": name},
    )
    return view


def delete_view(user, view_id: int) -> None:
    view = _get_owned(user, view_id)
    view.delete()
    audit.record(
        module="identity", action="delete_saved_view", entity_type="SavedView",
        entity_id=view_id, actor=user,
    )


def set_default(user, view_id: int) -> SavedView:
    """Make one view the default for its list; any previous default for that list is unset."""
    view = _get_owned(user, view_id)
    if not view.is_default:
        view.is_default = True
        view.save(update_fields=["is_default", "updated_at"])
    _clear_other_defaults(user, view.list_key, keep=view.pk)
    audit.record(
        module="identity", action="set_default_saved_view", entity_type="SavedView",
        entity_id=view.pk, actor=user,
    )
    return view


def _clear_other_defaults(user, list_key: str, keep: int) -> None:
    SavedView.objects.filter(user=user, list_key=list_key, is_default=True).exclude(pk=keep).update(
        is_default=False
    )
