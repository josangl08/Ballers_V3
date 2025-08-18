from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.player_model import Player

from .base import Base


class MLMetrics(Base):
    """
    Modelo para métricas de Machine Learning calculadas para jugadores profesionales.

    Incluye el Player Development Index (PDI) con arquitectura híbrida:
    - Métricas universales (40%): Aplicables a todas las posiciones
    - Métricas por zona (35%): Defensivas, mediocampo, ofensivas
    - Métricas específicas (25%): Por posición particular

    Utiliza modelo unificado con shared encoder + position heads.
    """

    __tablename__ = "ml_metrics"

    # Identificación principal
    metric_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.player_id", ondelete="CASCADE"), nullable=False
    )
    season: Mapped[str] = mapped_column(String, nullable=False)  # "2024-25"

    # === PLAYER DEVELOPMENT INDEX (PDI) ===
    # PDI Overall: Métrica compuesta final (0-100)
    pdi_overall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Componentes PDI por arquitectura híbrida
    pdi_universal: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Métricas universales (40%): pases, duelos, disciplina",
    )
    pdi_zone: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Métricas por zona (35%): defensivas, mediocampo, ofensivas",
    )
    pdi_position_specific: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Métricas específicas (25%): por posición particular",
    )

    # === MÉTRICAS DE RANKING Y PERCENTILES ===
    # Percentiles para comparación
    position_percentile: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Percentil dentro de su posición (0-100)"
    )
    league_percentile: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Percentil en toda la liga (0-100)"
    )

    # Rankings numéricos
    position_rank: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Ranking dentro de su posición"
    )
    league_rank: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Ranking en toda la liga"
    )

    # === MÉTRICAS COMPLEMENTARIAS ===
    # Métricas de desarrollo por área
    technical_proficiency: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Habilidades técnicas (0-100)"
    )
    tactical_intelligence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Inteligencia táctica (0-100)"
    )
    physical_performance: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Rendimiento físico (0-100)"
    )
    consistency_index: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Índice de consistencia (0-100)"
    )

    # === METADATA DEL MODELO ML ===
    # Información del cálculo
    model_version: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="1.0", comment="Versión del modelo ML utilizado"
    )
    position_analyzed: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Posición utilizada para el análisis"
    )
    features_used: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Número de features utilizados en el cálculo"
    )

    # Timestamps
    last_calculated: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        comment="Última vez que se calcularon las métricas",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, onupdate=datetime.utcnow
    )

    # === RELACIONES ===
    # Relación con Player
    player: Mapped[Player] = relationship("Player", back_populates="ml_metrics")

    def __repr__(self) -> str:
        return (
            f"MLMetrics(metric_id={self.metric_id}, "
            f"player_id={self.player_id}, "
            f"season='{self.season}', "
            f"pdi_overall={self.pdi_overall}, "
            f"position='{self.position_analyzed}')"
        )

    @property
    def pdi_breakdown(self) -> dict:
        """
        Devuelve el desglose completo del PDI para análisis.

        Returns:
            dict: Componentes del PDI con pesos aplicados
        """
        return {
            "pdi_overall": self.pdi_overall or 0.0,
            "components": {
                "universal": {
                    "score": self.pdi_universal or 0.0,
                    "weight": 0.40,
                    "contribution": (self.pdi_universal or 0.0) * 0.40,
                },
                "zone": {
                    "score": self.pdi_zone or 0.0,
                    "weight": 0.35,
                    "contribution": (self.pdi_zone or 0.0) * 0.35,
                },
                "position_specific": {
                    "score": self.pdi_position_specific or 0.0,
                    "weight": 0.25,
                    "contribution": (self.pdi_position_specific or 0.0) * 0.25,
                },
            },
            "development_areas": {
                "technical": self.technical_proficiency or 0.0,
                "tactical": self.tactical_intelligence or 0.0,
                "physical": self.physical_performance or 0.0,
                "consistency": self.consistency_index or 0.0,
            },
            "rankings": {
                "position_percentile": self.position_percentile or 0.0,
                "league_percentile": self.league_percentile or 0.0,
                "position_rank": self.position_rank or 0,
                "league_rank": self.league_rank or 0,
            },
        }

    @property
    def is_stale(self) -> bool:
        """
        Verifica si las métricas necesitan ser recalculadas.

        Returns:
            bool: True si han pasado más de 7 días desde el último cálculo
        """
        if not self.last_calculated:
            return True

        days_since_calculation = (datetime.utcnow() - self.last_calculated).days
        return days_since_calculation > 7

    def get_strength_areas(self, threshold: float = 75.0) -> list:
        """
        Identifica áreas de fortaleza del jugador.

        Args:
            threshold: Umbral para considerar una métrica como fortaleza

        Returns:
            list: Lista de áreas donde el jugador destaca
        """
        strengths = []
        areas = {
            "Technical Proficiency": self.technical_proficiency,
            "Tactical Intelligence": self.tactical_intelligence,
            "Physical Performance": self.physical_performance,
            "Consistency": self.consistency_index,
        }

        for area, score in areas.items():
            if score and score >= threshold:
                strengths.append(area)

        return strengths

    def get_improvement_areas(self, threshold: float = 50.0) -> list:
        """
        Identifica áreas que necesitan mejora.

        Args:
            threshold: Umbral por debajo del cual se considera área de mejora

        Returns:
            list: Lista de áreas que requieren trabajo
        """
        improvements = []
        areas = {
            "Technical Proficiency": self.technical_proficiency,
            "Tactical Intelligence": self.tactical_intelligence,
            "Physical Performance": self.physical_performance,
            "Consistency": self.consistency_index,
        }

        for area, score in areas.items():
            if score and score < threshold:
                improvements.append(area)

        return improvements
