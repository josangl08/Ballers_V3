from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
if TYPE_CHECKING:
    from .user_model import User

from .base import Base

class Admin(Base):
    __tablename__ = "admins"

    admin_id: Mapped[int]          = mapped_column(Integer, primary_key=True)
    user_id:  Mapped[int]          = mapped_column(ForeignKey("users.user_id"), unique=True, nullable=False)
    role:     Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="admin_profile")
