from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .user_model import Base

class Coach(Base):
    __tablename__ = "coaches"

    coach_id = Column(Integer, primary_key=True)
    user_id  = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    license  = Column(String)

    # Relaciones
    user     = relationship("User", back_populates="coach_profile")
    sessions = relationship("Session", back_populates="coach")