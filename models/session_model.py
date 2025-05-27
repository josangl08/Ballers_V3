from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
if TYPE_CHECKING:
    from models.coach_model import Coach
    from models.player_model import Player
from .base import Base


class SessionStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELED  = "canceled"


class Session(Base):
    __tablename__ = "sessions"

    id:          Mapped[int]               = mapped_column(Integer, primary_key=True)
    coach_id:    Mapped[int]               = mapped_column(ForeignKey("coaches.coach_id"), nullable=False)
    player_id:   Mapped[int]               = mapped_column(ForeignKey("players.player_id"), nullable=False)

    start_time:  Mapped[datetime]          = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    end_time:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status:      Mapped[SessionStatus]     = mapped_column(Enum(SessionStatus, native_enum=False),
                                                           default=SessionStatus.SCHEDULED)
    notes:       Mapped[Optional[str]]      = mapped_column(String, nullable=True)
    created_at:  Mapped[datetime]           = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Relaciones
    coach:  Mapped["Coach"]  = relationship(back_populates="sessions")
    player: Mapped["Player"] = relationship(back_populates="sessions")
