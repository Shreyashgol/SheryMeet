"""Generic repository base.

Repositories are the only place that talks to the ORM. Services depend on
repositories (not on `Session` details), which keeps persistence concerns out of
business logic and makes services unit-testable with in-memory fakes.

The base provides the common CRUD primitives; specialised repositories add
aggregate-specific queries.
"""

from __future__ import annotations

import uuid
from typing import Generic, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """CRUD operations shared by all repositories."""

    model: Type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ModelT) -> ModelT:
        """Stage a new entity for insertion and flush to obtain its identity."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        """Return an entity by primary key, or None."""
        return self.session.get(self.model, entity_id)

    def get_by(self, **filters: object) -> ModelT | None:
        """Return the first entity matching the given equality filters, or None."""
        stmt = select(self.model).filter_by(**filters).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def list(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Return a page of entities ordered by creation time (newest first)."""
        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return self.session.execute(stmt).scalars().all()

    def delete(self, entity: ModelT) -> None:
        """Delete an entity."""
        self.session.delete(entity)
        self.session.flush()
