from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.player_model import Player

from .base import Base


class ProfessionalStats(Base):
    """
    Modelo para estadísticas profesionales de jugadores de la liga tailandesa.
    Datos extraídos del repositorio GitHub de Wyscout_Prospect_Research.
    """

    __tablename__ = "professional_stats"

    # Identificación principal
    stat_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id"), nullable=False
    )
    wyscout_id: Mapped[str] = mapped_column(String, nullable=False)
    season: Mapped[str] = mapped_column(String, nullable=False)  # "2024-25"

    # Información básica del jugador
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str] = mapped_column(String, nullable=False)
    competition: Mapped[str] = mapped_column(String, default="Thai League")
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    birth_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    passport_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Información posicional
    primary_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    secondary_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    third_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Estadísticas básicas de rendimiento
    matches_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minutes_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Estadísticas defensivas
    defensive_actions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    defensive_duels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    defensive_duels_won: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aerial_duels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aerial_duels_won: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sliding_tackles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interceptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fouls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Estadísticas ofensivas
    shots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shot_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    goal_conversion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dribbles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dribbles_successful: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    progressive_runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Estadísticas de pases
    passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    passes_accurate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pass_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forward_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    back_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    long_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    long_passes_accurate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Métricas avanzadas
    expected_goals: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # xG
    expected_assists: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # xA
    progressive_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    key_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crosses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crosses_accurate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Disciplina
    yellow_cards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relación con el jugador
    player: Mapped["Player"] = relationship(back_populates="professional_stats")

    # Índice único para evitar duplicados
    __table_args__ = ({"sqlite_autoincrement": True},)

    def __repr__(self) -> str:
        return f"<ProfessionalStats(player={self.player_name}, season={self.season}, team={self.team})>"
