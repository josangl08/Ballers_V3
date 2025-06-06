from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
if TYPE_CHECKING:
    from models.coach_model import Coach
    from models.player_model import Player
    from models.admin_model import Admin
from .base import Base


class UserType(enum.Enum):
    admin  = "admin"
    coach  = "coach"
    player = "player"


class User(Base):
    __tablename__ = "users"

    user_id:        Mapped[int]               = mapped_column(Integer, primary_key=True)
    username:       Mapped[str]               = mapped_column(String, unique=True, nullable=False)
    name:           Mapped[str]               = mapped_column(String, nullable=False)
    password_hash:  Mapped[str]               = mapped_column(String, nullable=False)
    email:          Mapped[str]               = mapped_column(String, unique=True, nullable=False)
    phone:          Mapped[Optional[str]]     = mapped_column(String, nullable=True)
    line:           Mapped[Optional[str]]     = mapped_column(String, nullable=True)
    profile_photo:  Mapped[str]               = mapped_column(
        String,
        default="assets/profiles_photos/default_profile.png"
    )
    fecha_registro: Mapped[datetime]          = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    date_of_birth:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user_type:      Mapped[UserType]          = mapped_column(Enum(UserType, native_enum=False), nullable=False)
    permit_level:   Mapped[int]               = mapped_column(Integer, default=1)
    is_active:      Mapped[bool]              = mapped_column(Boolean, default=True)
    
    # Perfiles específicos (uno a uno)
    coach_profile:  Mapped[Optional["Coach"]]  = relationship(back_populates="user", uselist=False)
    player_profile: Mapped[Optional["Player"]] = relationship(back_populates="user", uselist=False)
    admin_profile:  Mapped[Optional["Admin"]]  = relationship(back_populates="user", uselist=False)
