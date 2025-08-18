from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
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
        ForeignKey("players.player_id", ondelete="CASCADE"), nullable=False
    )
    wyscout_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[str] = mapped_column(String, nullable=False)  # "2024-25"

    # Información básica del jugador
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str] = mapped_column(String, nullable=False)
    team_within_timeframe: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team_logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    competition: Mapped[str] = mapped_column(String, default="Thai League")
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    birth_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    passport_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Información posicional
    primary_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    secondary_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    third_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # === ESTADÍSTICAS BÁSICAS ===
    matches_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minutes_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    foot: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # === RENDIMIENTO OFENSIVO ===
    shots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shots_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shots_on_target_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    goal_conversion_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    goals_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    assists_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    touches_in_box_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shot_assists_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # === RENDIMIENTO DEFENSIVO ===
    defensive_actions_per_90: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    defensive_duels_per_90: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    defensive_duels_won_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    aerial_duels_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aerial_duels_won_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sliding_tackles_per_90: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    interceptions_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fouls_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # === PASES Y DISTRIBUCIÓN ===
    passes_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_accuracy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forward_passes_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forward_passes_accuracy_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    back_passes_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    back_passes_accuracy_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    long_passes_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    long_passes_accuracy_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    progressive_passes_per_90: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    progressive_passes_accuracy_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    key_passes_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # === DUELOS Y FÍSICO ===
    duels_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duels_won_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    offensive_duels_per_90: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    offensive_duels_won_pct: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    dribbles_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dribbles_success_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    progressive_runs_per_90: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # === MÉTRICAS AVANZADAS ===
    expected_goals: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # xG
    expected_assists: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # xA
    xg_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    xa_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # === DISCIPLINA ===
    yellow_cards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    yellow_cards_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    red_cards_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fouls_suffered_per_90: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relación con el jugador
    player: Mapped["Player"] = relationship(back_populates="professional_stats")

    # Índice único para evitar duplicados
    __table_args__ = ({"sqlite_autoincrement": True},)

    def __repr__(self) -> str:
        return f"<ProfessionalStats(player={self.player_name}, season={self.season}, team={self.team})>"
