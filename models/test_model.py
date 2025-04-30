from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .user_model import Base

class TestResult(Base):
    __tablename__ = "test_results"

    id                  = Column(Integer, primary_key=True)
    player_id           = Column(Integer, ForeignKey("players.player_id"), nullable=False)
    test_name           = Column(String, nullable=False)
    date                = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    weight              = Column(Float)   # Peso en kg
    height              = Column(Float)   # Altura en cm

    # Métricas de rendimiento
    ball_control        = Column(Float)
    control_pass        = Column(Float)
    receive_scan        = Column(Float)
    dribling_carriying  = Column(Float)
    shooting            = Column(Float)
    crossbar            = Column(Float)
    sprint              = Column(Float)
    t_test              = Column(Float)   # T-test (agilidad)
    jumping             = Column(Float)

    # Relaciones
    player              = relationship("Player", back_populates="test_results")