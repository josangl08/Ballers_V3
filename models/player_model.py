from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.user_model import User
    from models.session_model import Session
    from models.test_model import TestResult
    from models.professional_stats_model import ProfessionalStats
    from models.ml_metrics_model import MLMetrics

from .base import Base


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), unique=True, nullable=False
    )
    service: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    enrolment: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Campos para jugadores profesionales
    is_professional: Mapped[bool] = mapped_column(Boolean, default=False)
    wyscout_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, unique=True
    )

    user: Mapped["User"] = relationship(back_populates="player_profile")
    sessions: Mapped[list["Session"]] = relationship(back_populates="player")
    test_results: Mapped[list["TestResult"]] = relationship(back_populates="player")
    professional_stats: Mapped[list["ProfessionalStats"]] = relationship(
        back_populates="player"
    )
    ml_metrics: Mapped[list["MLMetrics"]] = relationship(back_populates="player")
