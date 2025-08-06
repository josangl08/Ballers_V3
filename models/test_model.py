from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.player_model import Player

from .base import Base


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id"), nullable=False
    )
    test_name: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Atributos corporales
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Métricas de rendimiento
    ball_control: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    control_pass: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    receive_scan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dribling_carriying: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shooting: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    crossbar: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sprint: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    t_test: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    jumping: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relaciones
    player: Mapped["Player"] = relationship(back_populates="test_results")