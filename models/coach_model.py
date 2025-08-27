from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.user_model import User
    from models.session_model import Session

from .base import Base


class Coach(Base):
    __tablename__ = "coaches"

    coach_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), unique=True, nullable=False
    )
    service: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    schedule_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hourly_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    certification: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="coach_profile")
    sessions: Mapped[list["Session"]] = relationship(back_populates="coach")
