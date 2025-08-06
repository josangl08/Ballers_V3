from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ImportStatus(enum.Enum):
    """Estados de importación de temporadas"""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    updated = "updated"


class ThaiLeagueSeason(Base):
    """
    Modelo para control de importaciones de temporadas de la liga tailandesa.
    Rastrea qué temporadas han sido importadas y su estado.
    """

    __tablename__ = "thai_league_seasons"

    # Identificación
    season_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )  # "2024-25"

    # Control de importación
    import_status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, native_enum=False), default=ImportStatus.pending
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_import_attempt: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Información del archivo fuente
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # MB

    # Estadísticas de importación
    total_records: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0
    )
    imported_records: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0
    )
    matched_players: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0
    )
    unmatched_players: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0
    )
    errors_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=0
    )

    # Logs y notas
    import_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuración de actualización
    auto_update_enabled: Mapped[bool] = mapped_column(
        Integer, default=True
    )  # Boolean como Integer
    update_frequency_days: Mapped[int] = mapped_column(
        Integer, default=7
    )  # Semanal por defecto

    def __repr__(self) -> str:
        return f"<ThaiLeagueSeason(season={self.season}, status={self.import_status.value})>"

    @property
    def is_current_season(self) -> bool:
        """Determina si esta es la temporada actual basándose en el año"""
        current_year = datetime.now().year
        season_years = self.season.split("-")
        if len(season_years) == 2:
            start_year = int(f"20{season_years[0]}")
            return start_year == current_year or start_year == current_year - 1
        return False

    @property
    def needs_update(self) -> bool:
        """Determina si la temporada necesita actualización"""
        if not self.auto_update_enabled:
            return False

        if self.last_import_attempt is None:
            return True

        # Fix: usar datetime.now(timezone.utc) en lugar de datetime.now() 
        # para evitar mezcla de naive y timezone-aware datetimes
        days_since_update = (datetime.now(timezone.utc) - self.last_import_attempt).days
        return days_since_update >= self.update_frequency_days

    def update_import_stats(
        self, total: int, imported: int, matched: int, unmatched: int, errors: int = 0
    ) -> None:
        """Actualiza las estadísticas de importación"""
        self.total_records = total
        self.imported_records = imported
        self.matched_players = matched
        self.unmatched_players = unmatched
        self.errors_count = errors
        self.last_import_attempt = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        """Marca la importación como completada"""
        self.import_status = ImportStatus.completed
        self.last_updated = datetime.now(timezone.utc)

    def mark_failed(self, error_message: str = None) -> None:
        """Marca la importación como fallida"""
        self.import_status = ImportStatus.failed
        self.last_updated = datetime.now(timezone.utc)
        if error_message:
            self.error_log = error_message
