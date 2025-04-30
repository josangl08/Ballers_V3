from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .user_model import Base

class Player(Base):
    __tablename__ = "players"

    player_id  = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    service    = Column(String)      # Ej. tipo de servicio contratado
    enrolment  = Column(Integer)     # Número de sesiones inscritas
    notes      = Column(String)

    # Relaciones
    user       = relationship("User", back_populates="player_profile")
    sessions   = relationship("Session", back_populates="player")
    test_results = relationship("TestResult", back_populates="player")