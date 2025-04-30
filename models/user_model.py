from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean
from sqlalchemy.orm import declarative_base, relationship
import enum
from datetime import datetime, timezone
from .base import Base


class UserType(enum.Enum):
    admin  = "admin"
    coach  = "coach"
    player = "player"

class User(Base):
    __tablename__ = "users"

    user_id        = Column(Integer, primary_key=True)
    username       = Column(String, unique=True, nullable=False)
    name           = Column(String, nullable=False)
    password_hash  = Column(String, nullable=False)
    email          = Column(String, unique=True, nullable=False)
    phone          = Column(String)
    line           = Column(String)                    # LINE de mensajería
    profile_photo  = Column(String, default="assets/profiles/default_profile.png")  # Ruta a la foto de perfil
    fecha_registro = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    date_of_birth  = Column(DateTime)
    user_type      = Column(Enum(UserType, native_enum=False), nullable=False)
    permit_level   = Column(Integer, default=1)
    is_active      = Column(Boolean, default=True)  # Para deshabilitar usuarios sin eliminarlos

    # Relaciones a perfiles específicos
    coach_profile  = relationship("Coach", back_populates="user", uselist=False)
    player_profile = relationship("Player", back_populates="user", uselist=False)
    admin_profile  = relationship("Admin", back_populates="user", uselist=False)