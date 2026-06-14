"""Repository base + transaction helper.

Database Safety Rule 1: business logic never touches the ORM/SQL directly — it goes through a
repository. Rule 2: all writes run inside a transaction with automatic rollback on failure.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generic, Iterator, TypeVar

from django.db import models, transaction

T = TypeVar("T", bound=models.Model)


@contextmanager
def atomic() -> Iterator[None]:
    """Run a unit of work atomically; any exception rolls the whole thing back."""
    with transaction.atomic():
        yield


class Repository(Generic[T]):
    """Thin, typed data-access boundary for a single model."""

    model: type[T]

    def get(self, pk) -> T | None:
        return self.model._default_manager.filter(pk=pk).first()

    def all(self) -> models.QuerySet[T]:
        return self.model._default_manager.all()

    def create(self, **fields) -> T:
        return self.model._default_manager.create(**fields)

    def filter(self, **lookups) -> models.QuerySet[T]:
        return self.model._default_manager.filter(**lookups)
