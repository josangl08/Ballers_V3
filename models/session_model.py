from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.coach_model import Coach
    from models.player_model import Player

from .base import Base


class SessionStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELED = "canceled"


# Nota: Usando ENUM nativo PostgreSQL para compatibilidad


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("coaches.coach_id"), nullable=True
    )
    player_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.player_id"), nullable=True
    )

    # Snapshots selectivos para usuarios eliminados
    coach_name_snapshot: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    player_name_snapshot: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status_enum", native_enum=True),
        default=SessionStatus.SCHEDULED,
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    calendar_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    sync_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    source: Mapped[str] = mapped_column(String(10), default="app")

    version: Mapped[int] = mapped_column(Integer, default=1)

    is_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    # Relaciones (opcionales para soportar eliminación de usuarios)
    coach: Mapped[Optional["Coach"]] = relationship(back_populates="sessions")
    player: Mapped[Optional["Player"]] = relationship(back_populates="sessions")
