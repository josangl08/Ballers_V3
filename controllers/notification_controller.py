# controllers/notification_controller.py
"""
Controlador para manejo de notificaciones de problemas de sincronización.
Separa la lógica de datos de la presentación UI.
"""
import datetime as dt
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Migrated to Dash - Streamlit imports removed

# Almacenamiento global para notificaciones (reemplaza st.session_state)
_global_notifications_store = {}


@dataclass
class SyncProblemsData:
    """
    Modelo de datos para problemas de sincronización.
    Estructura limpia y tipada para manejar los datos.
    """

    rejected: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    timestamp: str
    seen: bool = False
    duration: float = 0.0
    imported: int = 0
    updated: int = 0
    deleted: int = 0

    def has_problems(self) -> bool:
        """Verifica si hay problemas (rechazados o warnings)."""
        return bool(self.rejected or self.warnings)

    def problem_count(self) -> int:
        """Cuenta total de problemas."""
        return len(self.rejected) + len(self.warnings)

    def get_age_minutes(self) -> float:
        """Calcula la edad en minutos desde el timestamp."""
        try:
            problem_time = dt.datetime.strptime(self.timestamp, "%d/%m/%Y %H:%M:%S")
            current_time = dt.datetime.now()
            return (current_time - problem_time).total_seconds() / 60
        except (ValueError, TypeError):
            return float("inf")  # Si hay error, considerar como muy antiguo


class NotificationController:
    """
    Controlador para manejo de notificaciones de problemas de sync - MIGRADO A DASH.
    Centraliza toda la lógica de datos sin depender de UI.
    """

    # Clave para almacenamiento global (reemplaza session_state)
    STORAGE_KEY = "sync_problems"

    def save_problems(
        self, rejected_events: List[Dict], warning_events: List[Dict]
    ) -> None:
        """
        Guarda problemas de sincronización del sync ACTUAL.
        Siempre reemplaza datos anteriores con datos del sync actual.

        Args:
            rejected_events: Lista de eventos rechazados
            warning_events: Lista de eventos con advertencias
        """
        try:
            # Crear timestamp actual
            current_timestamp = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            # Crear estructura de datos
            problems_data = SyncProblemsData(
                rejected=rejected_events,
                warnings=warning_events,
                timestamp=current_timestamp,
                seen=False,
            )

            # Guardar en almacenamiento global usando dataclass
            global _global_notifications_store
            _global_notifications_store[self.STORAGE_KEY] = problems_data

            # Log solo si hay datos útiles
            if rejected_events or warning_events:
                print(
                    f"💾 Sync problems saved: {len(rejected_events)} rejected, "
                    f"{len(warning_events)} warnings ({current_timestamp})"
                )
            else:
                # Log de limpieza solo en debug
                if os.getenv("DEBUG", "False") == "True":
                    print(f"💾 Sync problems cleared ({current_timestamp})")

        except Exception as e:
            print(f"❌ ERROR saving sync_problems: {e}")

    def get_problems(self) -> Optional[SyncProblemsData]:
        """
        Obtiene problemas de sincronización guardados.

        Returns:
            SyncProblemsData o None si no hay datos válidos
        """
        global _global_notifications_store
        try:
            # Verificar si existe en almacenamiento global
            if self.STORAGE_KEY not in _global_notifications_store:
                return None

            # Obtener el valor
            problems = _global_notifications_store[self.STORAGE_KEY]

            # Si es el formato anterior (dict), convertir a dataclass
            if isinstance(problems, dict):
                return self._migrate_old_format(problems)

            # Si ya es dataclass, verificar que sea válido
            if isinstance(problems, SyncProblemsData):
                return problems

            # Formato no reconocido
            return None

        except Exception as e:
            # Si hay error, limpiar datos corruptos
            if self.STORAGE_KEY in _global_notifications_store:
                del _global_notifications_store[self.STORAGE_KEY]
            print(f"⚠️ Error getting sync problems: {e}")
            return None


    def has_problems(self) -> bool:
        """
        Verifica si hay problemas de sincronización pendientes.

        Returns:
            True si hay problemas rechazados o warnings
        """
        problems = self.get_problems()
        return problems.has_problems() if problems else False

    def clear_all(self) -> None:
        """Limpia todos los problemas guardados."""
        global _global_notifications_store
        keys_to_remove = [
            self.STORAGE_KEY,
            "last_rejected_events",
            "last_warning_events",
            "last_sync_time",
        ]

        for key in keys_to_remove:
            if key in _global_notifications_store:
                del _global_notifications_store[key]

    def mark_as_seen(self) -> None:
        """Marca los problemas como vistos por el usuario."""
        global _global_notifications_store
        problems = self.get_problems()
        if problems:
            problems.seen = True
            _global_notifications_store[self.STORAGE_KEY] = problems

    def cleanup_old_problems(self, max_age_hours: int = 24) -> None:
        """
        Limpia automáticamente problemas antiguos.

        Args:
            max_age_hours: Máximo tiempo en horas para mantener problemas
        """
        problems = self.get_problems()

        if not problems:
            return

        age_minutes = problems.get_age_minutes()
        max_age_minutes = max_age_hours * 60

        # Limpiar si es muy antiguo
        if age_minutes > max_age_minutes:
            self.clear_all()
            print(f"🧹 Auto-cleaned problems older than {max_age_hours}h")

    def get_summary_text(self) -> str:
        """
        Devuelve resumen textual de problemas para logs o mensajes.

        Returns:
            String con resumen, vacío si no hay problemas
        """
        problems = self.get_problems()

        if not problems or not problems.has_problems():
            return ""

        parts = []

        if problems.rejected:
            parts.append(f"{len(problems.rejected)} rechazados")

        if problems.warnings:
            parts.append(f"{len(problems.warnings)} con advertencias")

        if parts:
            return f"Problemas de sync: {', '.join(parts)}"

        return ""

    # Métodos de migración y compatibilidad

    def _migrate_old_format(self, old_data: Dict) -> Optional[SyncProblemsData]:
        """
        Migra formato anterior (dict) al nuevo formato (dataclass).
        Mantiene compatibilidad con versiones anteriores.
        """
        try:
            return SyncProblemsData(
                rejected=old_data.get("rejected", []),
                warnings=old_data.get("warnings", []),
                timestamp=old_data.get(
                    "timestamp", dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                ),
                seen=old_data.get("seen", False),
            )
        except Exception as e:
            print(f"⚠️ Error migrating old format: {e}")
            return None

    # Métodos de análisis y filtrado

    def filter_problems_by_recency(
        self, max_age_minutes: int = 120
    ) -> Optional[SyncProblemsData]:
        """
        Obtiene solo problemas recientes.

        Args:
            max_age_minutes: Máximo tiempo en minutos para considerar reciente

        Returns:
            SyncProblemsData solo si es reciente, None si es antiguo
        """
        problems = self.get_problems()

        if not problems:
            return None

        age_minutes = problems.get_age_minutes()

        if age_minutes <= max_age_minutes:
            return problems

        return None

    def get_recent_problems_for_ui(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene problemas formateados para UI, solo si son recientes.

        Returns:
            Dict con datos para UI o None si no hay problemas recientes
        """
        problems = self.filter_problems_by_recency(max_age_minutes=5)  # 5 minutos

        if not problems or not problems.has_problems():
            return None

        return {
            "rejected_count": len(problems.rejected),
            "warnings_count": len(problems.warnings),
            "total_count": problems.problem_count(),
            "timestamp": problems.timestamp,
            "age_minutes": problems.get_age_minutes(),
            "seen": problems.seen,
            "rejected_events": problems.rejected,
            "warning_events": problems.warnings,
        }


def save_sync_problems(rejected_events: List[Dict], warning_events: List[Dict]) -> None:
    """
    Función de conveniencia para mantener compatibilidad.
    Delega al NotificationController.
    """
    controller = NotificationController()
    controller.save_problems(rejected_events, warning_events)


def get_sync_problems() -> Optional[Dict[str, Any]]:
    """
    Función de conveniencia para mantener compatibilidad.
    Devuelve formato dict para compatibilidad con código existente.
    """
    controller = NotificationController()
    problems = controller.get_problems()

    if not problems:
        return None

    # Estructura base
    result = {
        "rejected": problems.rejected,
        "warnings": problems.warnings,
        "timestamp": problems.timestamp,
        "seen": problems.seen,
    }

    # Incluir stats adicionales si vienen del fallback
    if hasattr(problems, "duration"):
        result["stats"] = {
            "duration": getattr(problems, "duration", 0),
            "imported": getattr(problems, "imported", 0),
            "updated": getattr(problems, "updated", 0),
            "deleted": getattr(problems, "deleted", 0),
        }

    return result


def clear_sync_problems() -> None:
    """Función de conveniencia para limpiar problemas."""
    controller = NotificationController()
    controller.clear_all()


def auto_cleanup_old_problems(max_age_hours: int = 24) -> None:
    """Función de conveniencia para limpieza automática."""
    controller = NotificationController()
    controller.cleanup_old_problems(max_age_hours)


def has_sync_problems() -> bool:
    """Función de conveniencia para verificar si hay problemas."""
    controller = NotificationController()
    return controller.has_problems()


def get_problems_summary() -> str:
    """Función de conveniencia para obtener resumen."""
    controller = NotificationController()
    return controller.get_summary_text()


# Funciones para UI


def get_notification_controller() -> NotificationController:
    """
    Factory function para obtener instancia del controller.
    Útil para casos avanzados que requieren acceso directo.
    """
    return NotificationController()


def get_problems_for_display(location: str = "general") -> Optional[Dict[str, Any]]:
    """
    Obtiene problemas formateados específicamente para display en UI.

    Args:
        location: Contexto donde se mostrará ("sidebar", "settings", "dashboard")

    Returns:
        Dict con datos formateados para UI o None
    """
    controller = NotificationController()

    # Para sidebar, solo problemas muy recientes
    if location == "sidebar":
        return controller.get_recent_problems_for_ui()

    # Para otros contextos, problemas más antiguos son aceptables
    problems = controller.get_problems()

    if not problems or not problems.has_problems():
        return None

    return {
        "rejected_count": len(problems.rejected),
        "warnings_count": len(problems.warnings),
        "total_count": problems.problem_count(),
        "timestamp": problems.timestamp,
        "age_minutes": problems.get_age_minutes(),
        "seen": problems.seen,
        "rejected_events": problems.rejected,
        "warning_events": problems.warnings,
        "location": location,
    }
