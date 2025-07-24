# controllers/calendar_utils.py
"""
Utilidades compartidas para manejo de calendario y sesiones.
Funciones puras sin dependencias externas.
"""
import datetime as dt
import hashlib
import logging
import re
from typing import Optional
from zoneinfo import ZoneInfo

from unidecode import unidecode

from config import CALENDAR_COLORS
from controllers.db import get_db_session
from models import Session, SessionStatus, User

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Europe/Madrid")


def format_time_local(dt_obj: Optional[dt.datetime]) -> str:
    """Convierte datetime UTC a hora local Madrid para logging legible"""
    if dt_obj is None:
        return "None"

    # Asegurar que tiene timezone info
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)

    # Convertir a hora de Madrid
    local_time = dt_obj.astimezone(LOCAL_TZ)
    return local_time.strftime("%H:%M")


def normalize_datetime_for_hash(dt_obj) -> str:
    """
     Normaliza datetime para hash: convierte a UTC y quita timezone info
    Maneja correctamente datetime naive desde timezone local
    """
    if dt_obj is None:
        return ""

    # Si es string, convertir a datetime primero
    if isinstance(dt_obj, str):
        try:
            dt_obj = dt.datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
        except Exception:
            return dt_obj  # Si falla, devolver como está

    # Lógica mejorada para datetime naive
    if dt_obj.tzinfo is None:
        # Asumir que datetime naive es en timezone local (Madrid)
        try:
            local_tz = ZoneInfo("Europe/Madrid")
            dt_obj = dt_obj.replace(tzinfo=local_tz)
            logger.debug(f"🌍 Datetime naive convertido a Madrid timezone: {dt_obj}")
        except Exception:
            # Si falla ZoneInfo, usar offset fijo +02:00
            dt_obj = dt_obj.replace(tzinfo=dt.timezone(dt.timedelta(hours=2)))
            logger.debug(f"🌍 Datetime naive convertido a +02:00: {dt_obj}")

    # Convertir a UTC y quitar timezone info para consistencia
    utc_naive = dt_obj.astimezone(dt.timezone.utc).replace(tzinfo=None)

    # Devolver formato ISO sin microsegundos
    result = utc_naive.replace(microsecond=0).isoformat()
    logger.debug(f"🔧 Normalización final: {dt_obj} → {result}")
    return result


def calculate_session_hash(session: Session) -> str:
    """Calcula hash MD5 basado en datos importantes de la sesión
    CON FECHAS NORMALIZADAS."""
    try:
        # Normalizar fechas
        start_normalized = normalize_datetime_for_hash(session.start_time)
        end_normalized = normalize_datetime_for_hash(session.end_time)

        data = "|".join(
            [
                str(session.coach_id),
                str(session.player_id),
                start_normalized,
                end_normalized,
                session.status.value,
                session.notes or "",
            ]
        )

        hash_result = hashlib.md5(
            data.encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        logger.debug(f"🔧 Session hash data: '{data}' → {hash_result[:8]}...")
        return hash_result

    except Exception as e:
        logger.warning(f"⚠️ Error calculando hash sesión #{session.id}: {e}")
        return ""


def calculate_event_hash(event_data: dict) -> str:
    """Calcula hash MD5 basado en datos importantes del evento
    CON FECHAS NORMALIZADAS."""
    try:

        def _to_dt_local(iso: str) -> dt.datetime:
            return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))

        # Obtener fechas del evento y normalizarlas
        start_dt = _to_dt_local(event_data["start"]["dateTime"])
        end_dt = _to_dt_local(event_data["end"]["dateTime"])

        start_normalized = normalize_datetime_for_hash(start_dt)
        end_normalized = normalize_datetime_for_hash(end_dt)

        # Importar aquí para evitar circular import
        status = status_from_color(event_data.get("colorId", "9"))

        props = event_data.get("extendedProperties", {}).get("private", {})
        coach_id = props.get("coach_id", "")
        player_id = props.get("player_id", "")

        data = "|".join(
            [
                str(coach_id),
                str(player_id),
                start_normalized,
                end_normalized,
                status.value,
                event_data.get("description", "") or "",
            ]
        )

        hash_result = hashlib.md5(
            data.encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        logger.debug(f"🔧 Event hash data: '{data}' → {hash_result[:8]}...")
        return hash_result

    except Exception as e:
        logger.warning(f"⚠️ Error calculando hash evento: {e}")
        return ""


def build_calendar_event_body(session: Session) -> dict:
    """Devuelve el diccionario body que Calendar API espera."""

    COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()}

    return {
        "summary": (
            f"Session: {session.coach.user.name} × {session.player.user.name} "
            f"#C{session.coach_id} #P{session.player_id}"
        ),
        "description": session.notes or "",
        "start": {
            "dateTime": session.start_time.astimezone(dt.timezone.utc).isoformat()
        },
        "end": {"dateTime": session.end_time.astimezone(dt.timezone.utc).isoformat()},
        "colorId": COLOR[session.status.value],
        "extendedProperties": {
            "private": {
                "session_id": str(session.id),
                "coach_id": str(session.coach_id),
                "player_id": str(session.player_id),
            }
        },
    }


def update_session_tracking(session: Session):
    """Actualiza campos de tracking después de cambios."""
    try:
        session.sync_hash = calculate_session_hash(session)
        session.updated_at = dt.datetime.now(dt.timezone.utc)
        session.last_sync_at = dt.datetime.now(dt.timezone.utc)
        session.is_dirty = False
        session.version = (session.version or 0) + 1

        logger.debug(
            f"📝 Tracking actualizado: Sesión #{session.id} v{session.version}"
        )
    except Exception as e:
        logger.warning(f"⚠️ Error actualizando tracking sesión #{session.id}: {e}")


def update_session_tracking_with_hash(session: Session, cached_hash: str):
    """Actualiza tracking usando hash cacheado - OPTIMIZACIÓN."""
    try:
        session.sync_hash = cached_hash  # Usa hash cacheado
        session.updated_at = dt.datetime.now(dt.timezone.utc)
        session.last_sync_at = dt.datetime.now(dt.timezone.utc)
        session.is_dirty = False
        session.version = (session.version or 0) + 1

        logger.debug(
            f"📝 Tracking actualizado (optimizado): "
            f"Sesión #{session.id} v{session.version}"
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Error actualizando tracking optimizado " f"sesión #{session.id}: {e}"
        )


def session_has_real_changes(session: Session) -> bool:
    """Verifica si una sesión tiene cambios REALES que justifiquen update"""
    # Si está marcada como dirty → hay cambios
    if hasattr(session, "is_dirty") and session.is_dirty:
        logger.debug(f"🔄 Sesión #{session.id} marcada como dirty")
        return True

    # Si no tiene hash → primera vez
    if not session.sync_hash:
        logger.debug(f"🔄 Sesión #{session.id} sin hash - primera sincronización")
        return True

    # Comparar hash actual vs. guardado
    current_hash = calculate_session_hash(session)

    if session.sync_hash != current_hash:
        logger.debug(
            f"🔄 Sesión #{session.id} hash cambió: "
            f"{session.sync_hash[:8]}... → {current_hash[:8]}..."
        )
        return True

    # Sin cambios reales
    logger.debug(f"✅ Sesión #{session.id} - sin cambios reales")
    return False


def session_needs_update(session: Session) -> bool:
    """Versión simple - Solo actualizar si está dirty o no tiene hash"""
    # 1. Si está dirty → actualizar
    if hasattr(session, "is_dirty") and session.is_dirty:
        return True

    # 2. Si no tiene hash → actualizar
    if not session.sync_hash:
        return True

    # 3. Verificar cambios en hash
    current_hash = calculate_session_hash(session)
    has_changes = session.sync_hash != current_hash

    if has_changes:
        logger.debug(f"🔄 Sesión #{session.id} - cambios detectados en hash")

    return has_changes


# Utilidades de parsing y mapeo


def safe_int(value):
    """Convierte valor a int de forma segura."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_text(text: str) -> str:
    """Pasa a minúsculas, quita tildes y unifica espacios."""
    return re.sub(r"\s+", " ", unidecode(text or "").strip().lower())


def extract_id_from_text(text: str, pattern: str):
    """Busca con regex y devuelve el grupo 1 como int, o None."""
    m = re.search(pattern, text, flags=re.I)
    return safe_int(m.group(1)) if m else None


def find_unique_user(model_class, name_norm: str):
    """
    Trae todos los registros del modelo (Coach o Player),
    normaliza user.name y devuelve el único que coincide con name_norm.
    Si hay 0 o >1, devuelve None.
    """

    db = get_db_session()
    try:
        rows = db.query(model_class).join(User).filter(User.is_active).all()
        matches = [r for r in rows if normalize_text(r.user.name) == name_norm]
        return matches[0] if len(matches) == 1 else None
    finally:
        db.close()


def status_from_color(color: str) -> SessionStatus:
    """
    Dado un colorId de Google Calendar, devuelve el estado correspondiente.
    • Reds → CANCELED
    • Greens → COMPLETED
    • El resto → SCHEDULED
    """
    cid = str(color)

    # Todos los rojos → canceled
    red_ids = {"11", "6"}
    if cid in red_ids:
        return SessionStatus.CANCELED

    # Todos los verdes → completed
    green_ids = {"2", "10"}
    if cid in green_ids:
        return SessionStatus.COMPLETED

    # El resto → scheduled
    return SessionStatus.SCHEDULED
