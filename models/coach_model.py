from __future__ import annotations
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.user_model import User
    from models.session_model import Session

from .base import Base

class Coach(Base):
    __tablename__ = "coaches"

    coach_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id:  Mapped[int] = mapped_column(ForeignKey("users.user_id"), unique=True, nullable=False)
    license:  Mapped[str] = mapped_column(String, nullable=True)

    user:     Mapped["User"]               = relationship(back_populates="coach_profile")
    sessions: Mapped[list["Session"]]      = relationship(back_populates="coach")
