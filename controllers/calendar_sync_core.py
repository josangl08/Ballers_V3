# controllers/calendar_sync_core.py
"""
Núcleo de sincronización con Google Calendar.
Maneja la sincronización bidireccional sin coordinar auto-sync ni estadísticas.
"""
import datetime as dt
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from googleapiclient.errors import HttpError
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config import CALENDAR_COLORS
from controllers.db import get_db_session
from controllers.google_client import calendar
from controllers.validation_controller import validate_session_for_import
from models import Coach, Player, Session, SessionStatus, User

from .calendar_utils import (
    build_calendar_event_body,
    calculate_event_hash,
    calculate_session_hash,
    extract_id_from_text,
    find_unique_user,
    format_time_local,
    normalize_text,
    safe_int,
    session_needs_update,
    status_from_color,
    update_session_tracking,
)
from .session_controller import SessionController

logger = logging.getLogger(__name__)

CAL_ID = os.getenv("CALENDAR_ID")
LOCAL_TZ = dt.timezone(dt.timedelta(hours=2))  # Madrid timezone simplificado


def guess_coach_player_ids(event: dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Estrategia para extraer coach_id y player_id:
    1) Extended properties (automático)
    2) Parsing híbrido: nombres + IDs opcionales
    3) Solo nombres (fuzzy)
    4) Solo IDs (#C #P)
    """
    props = event.get("extendedProperties", {}).get("private", {})

    # Extended properties (solo si válidos)
    cid = safe_int(props.get("coach_id"))
    pid = safe_int(props.get("player_id"))
    if cid and pid and cid < 100 and pid < 100:
        return cid, pid

    summary = event.get("summary", "") or ""

    # Parsing híbrido: nombres + IDs opcionales
    # Limpiar prefijo "Sesión:" / "Session:"
    summary_clean = re.sub(
        r"^(?:sesión|session)[:\-]\s*", "", summary, flags=re.IGNORECASE
    )

    # Buscar patrón: [algo] × [algo] o [algo] x [algo]
    match = re.search(r"(.+?)\s*[×x]\s*(.+)", summary_clean, re.IGNORECASE)

    if match:
        left_part = match.group(1).strip()  # Lado coach
        right_part = match.group(2).strip()  # Lado player

        coach_id = player_id = None

        # Analizar coach (izquierda)
        coach_id_match = re.search(r"#[Cc](\d+)", left_part)
        if coach_id_match:
            # Hay ID explícito → usarlo
            coach_id = int(coach_id_match.group(1))
        else:
            # No hay ID → buscar por nombre
            coach_name = left_part.strip()
            coach_name_norm = normalize_text(coach_name)
            coach_obj = find_unique_user(Coach, coach_name_norm)
            if coach_obj:
                coach_id = coach_obj.coach_id

        # Analizar Player (derecha)
        player_id_match = re.search(r"#[Pp](\d+)", right_part)
        if player_id_match:
            # Hay ID explícito → usarlo
            player_id = int(player_id_match.group(1))
        else:
            # No hay ID → buscar por nombre
            player_name = right_part.strip()
            player_name_norm = normalize_text(player_name)
            player_obj = find_unique_user(Player, player_name_norm)
            if player_obj:
                player_id = player_obj.player_id

        # Si encontramos ambos, devolver
        if coach_id and player_id:
            return coach_id, player_id

    # Fallback: Solo IDs tradicionales #C #P (anywhere en título)
    cid = extract_id_from_text(summary, r"#C(\d+)") or extract_id_from_text(
        summary, r"Coach[#\s]*(\d+)"
    )
    pid = extract_id_from_text(summary, r"#P(\d+)") or extract_id_from_text(
        summary, r"Player[#\s]*(\d+)"
    )
    if cid and pid:
        return cid, pid

    return None, None


def patch_event_after_import(session: Session, event_id: str):
    """
    Parcha un evento importado: añade IDs y formatea el título.
    Solo si realmente es necesario.
    """
    try:
        # Verificar si el evento ya tiene los datos correctos
        current_event = (
            calendar().events().get(calendarId=CAL_ID, eventId=event_id).execute()
        )

        props = current_event.get("extendedProperties", {}).get("private", {})
        session_id_in_event = props.get("session_id")
        current_color = current_event.get("colorId", "9")

        # Verificar si necesita actualización
        needs_update = False

        # Si no tiene session_id correcto
        if session_id_in_event != str(session.id):
            needs_update = True

        # Si tiene color desconocido, normalizarlo
        valid_colors = [v["google"] for v in CALENDAR_COLORS.values()]
        if current_color not in valid_colors:
            needs_update = True
            logger.info(
                f"🎨 Color desconocido {current_color} → normalizando a scheduled"
            )

        # Si ya tiene el session_id correcto, no hacer nada
        if not needs_update:
            logger.debug(f"✅ Evento {event_id[:8]}... ya tiene datos correctos")
            return

        # Solo patchear si realmente es necesario
        db = get_db_session()
        try:
            coach_name = (
                db.query(User.name)
                .join(Coach)
                .filter(Coach.coach_id == session.coach_id)
                .scalar()
            )
            player_name = (
                db.query(User.name)
                .join(Player)
                .filter(Player.player_id == session.player_id)
                .scalar()
            )

            # Determinar color correcto basado en estado de sesión
            COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()}
            correct_color = COLOR[session.status.value]

            patch_body = {
                "summary": f"Session: {coach_name} × {player_name}  #C{session.coach_id} #P{session.player_id}",
                "colorId": correct_color,  # Normalizar color
                "extendedProperties": {
                    "private": {
                        "session_id": str(session.id),
                        "coach_id": str(session.coach_id),
                        "player_id": str(session.player_id),
                    }
                },
            }

            calendar().events().patch(
                calendarId=CAL_ID, eventId=event_id, body=patch_body
            ).execute()

            logger.info(f"🔧 Evento {event_id[:8]}... actualizado correctamente")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error actualizando evento {event_id[:8]}...: {e}")


def update_session_in_calendar_only(session: Session):
    """Actualiza evento en Calendar sin tocar la sesión BD actual."""
    if not session.calendar_event_id:
        logger.warning(f"⚠️ Sesión #{session.id} sin event_id")
        return

    try:
        body = build_calendar_event_body(session)
        calendar().events().patch(
            calendarId=CAL_ID, eventId=session.calendar_event_id, body=body
        ).execute()
        logger.debug(
            f"📤 Evento {session.calendar_event_id[:8]}... actualizado desde BD"
        )

    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(
                f"⚠️ Evento {session.calendar_event_id[:8]}... no existe en Calendar"
            )
        else:
            logger.error(f"❌ Error actualizando evento en Calendar: {e}")
            raise


def sync_calendar_to_db_with_feedback() -> Tuple[int, int, int, List[Dict], List[Dict]]:
    """
    Sincroniza eventos de Google Calendar hacia la base de datos con logging detallado.

    Returns:
        Tuple (imported, updated, deleted, rejected_events, warning_events)
    """
    start_time = time.time()
    logger.info("🔄 INICIANDO sincronización Calendar → BD")

    svc = calendar()
    db = get_db_session()

    rejected_events = []  # Lista de eventos rechazados
    warning_events = []  # Lista de eventos con warnings

    try:
        imported = updated = deleted = 0
        seen_ev_ids: set[str] = set()

        now = dt.datetime.now(dt.timezone.utc)
        # Ventana configurable por variables de entorno (valores por defecto: 10 atrás, 20 adelante)
        past_days = int(os.getenv("SYNC_WINDOW_PAST_DAYS", "10"))
        future_days = int(os.getenv("SYNC_WINDOW_FUTURE_DAYS", "20"))
        win_start = now - dt.timedelta(days=past_days)
        win_end = now + dt.timedelta(days=future_days)

        logger.info(
            f"📅 Ventana de sincronización: {win_start.date()} a {win_end.date()} "
            f"(past={past_days}d, future={future_days}d)"
        )

        # Obtener eventos de Google Calendar
        logger.info("📡 Obteniendo eventos de Google Calendar...")
        events_response = (
            svc.events()
            .list(
                calendarId=CAL_ID,
                timeMin=win_start.isoformat(),
                timeMax=win_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_response.get("items", [])
        logger.info(f"📋 Encontrados {len(events)} eventos en Google Calendar")

        def _to_dt(iso: str) -> dt.datetime:
            # Convertir UTC de Google Calendar a Madrid timezone (+2) como naive
            utc_dt = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
            madrid_dt = utc_dt.astimezone(dt.timezone(dt.timedelta(hours=2)))
            return madrid_dt.replace(tzinfo=None)

        # Cargar todas las sesiones con calendar_event_id ya guardado
        logger.info("🗄️ Cargando sesiones existentes de la BD...")
        db_sessions = {
            s.calendar_event_id: s
            for s in db.query(Session).filter(Session.calendar_event_id != None).all()
        }
        logger.info(f"💾 Encontradas {len(db_sessions)} sesiones con event_id en BD")

        # Procesar cada evento de Google Calendar
        for i, ev in enumerate(events, 1):
            ev_id = ev["id"]
            seen_ev_ids.add(ev_id)

            if i % 10 == 0:  # Log progreso cada 10 eventos
                logger.info(f"⏳ Procesando evento {i}/{len(events)}")

            props = ev.get("extendedProperties", {}).get("private", {})
            sess_id = props.get("session_id")
            start_dt = _to_dt(ev["start"]["dateTime"])
            end_dt = _to_dt(ev["end"]["dateTime"])
            status = status_from_color(ev.get("colorId", "9"))

            # Busqueda de sesion existente
            ses = None

            # 1. Buscar por session_id en extended properties
            if sess_id and sess_id.isdigit():
                ses = db.get(Session, int(sess_id))
                if ses:
                    logger.debug(f"✅ Encontrada por session_id: {sess_id}")

            # 2. Buscar por calendar_event_id (MÁS COMÚN)
            if not ses:
                ses = db_sessions.get(ev_id)
                if ses:
                    logger.debug(f"✅ Encontrada por event_id: {ev_id[:8]}...")

            # Busqueda Fuzzy como último recurso
            if not ses:
                coach_id, player_id = guess_coach_player_ids(ev)
                if coach_id and player_id:
                    # Buscar sesión sin event_id que coincida en fecha/coach/player
                    potential_matches = (
                        db.query(Session)
                        .filter(
                            Session.coach_id == coach_id,
                            Session.player_id == player_id,
                            Session.calendar_event_id == None,
                            func.date(Session.start_time) == start_dt.date(),
                        )
                        .all()
                    )

                    if potential_matches:
                        ses = potential_matches[0]
                        ses.calendar_event_id = ev_id  # Vincular evento
                        logger.info(
                            f"🔗 MATCH FUZZY: Sesión #{ses.id} vinculada al evento {ev_id[:8]}..."
                        )
                        db.add(ses)
                        db.flush()

            if ses:
                # Sesión existente - verificar cambios

                # Verificar si event_id coincide
                if ses.calendar_event_id != ev_id:
                    logger.debug(
                        f"🔗 Actualizando event_id: {ses.calendar_event_id} → {ev_id}"
                    )
                    ses.calendar_event_id = ev_id
                    db.add(ses)
                    db.flush()

                # HASH COMPARISON - Prioridad máxima
                current_hash = ses.sync_hash or ""

                # Si no tiene hash, calcularlo ahora (sesión antigua)
                if not current_hash:
                    try:
                        current_hash = calculate_session_hash(ses)
                        ses.sync_hash = current_hash
                        logger.debug(f"🔧 Hash inicial calculado para sesión #{ses.id}")
                    except Exception as e:
                        logger.warning(
                            f"⚠️  Error calculando hash de sesión #{ses.id}: {e}"
                        )
                        # Usar hash por defecto para evitar fallos
                        current_hash = (
                            f"default_{ses.id}_{int(ses.start_time.timestamp())}"
                        )
                        ses.sync_hash = current_hash

                try:
                    event_hash = calculate_event_hash(ev)
                except Exception as e:
                    logger.warning(f"⚠️  Error calculando hash de evento: {e}")
                    # Usar hash por defecto para evitar fallos
                    event_hash = f"event_{ev.get('id', 'unknown')}"

                logger.debug(
                    f"🔍 Hash check Sesión #{ses.id}: BD='{current_hash[:8]}...' vs Event='{event_hash[:8]}...'"
                )

                #  Si hashes coinciden → No hay cambios reales
                if current_hash == event_hash:
                    logger.debug(f"✅ Sesión #{ses.id} - hashes coinciden, sin cambios")
                    continue

                # Hashes diferentes → Hay cambios reales, decidir quién gana

                # Verificar si sesión está marcada como dirty (cambios locales pendientes)
                if hasattr(ses, "is_dirty") and ses.is_dirty:
                    # Sesión local tiene cambios pendientes → APP wins
                    logger.info(
                        f"🔄 APP WINS - Sesión #{ses.id} (cambios locales pendientes)"
                    )
                    logger.info(
                        f"📝 BD→CALENDAR: Forzando actualización de evento desde sesión #{ses.id}"
                    )

                    try:
                        ses.is_dirty = False
                        ses.last_sync_at = dt.datetime.now(dt.timezone.utc)
                        update_session_in_calendar_only(ses)
                        logger.info(
                            f"✅ Evento actualizado en Calendar desde BD (APP WINS)"
                        )
                    except Exception as e:
                        logger.error(f"❌ Error actualizando Calendar desde BD: {e}")
                        ses.is_dirty = True
                        db.add(ses)

                    continue

                # Análisis de timestamps (solo como tiebreaker)
                event_updated_str = ev.get("updated") or ev.get("created") or ""
                event_updated = None
                session_updated = ses.updated_at or ses.created_at

                calendar_wins = True  # Default: Calendar wins
                conflict_reason = "hash_different_calendar_default"

                if event_updated_str and session_updated:
                    try:
                        event_updated = dt.datetime.fromisoformat(
                            event_updated_str.replace("Z", "+00:00")
                        )
                        if event_updated.tzinfo is None:
                            event_updated = event_updated.replace(
                                tzinfo=dt.timezone.utc
                            )

                        if session_updated and session_updated.tzinfo is None:
                            session_updated = session_updated.replace(
                                tzinfo=dt.timezone.utc
                            )

                        time_diff = (session_updated - event_updated).total_seconds()
                        time_diff_abs = abs(time_diff)

                        # Solo usar timestamps para diferencais significativas (>10 segundos)
                        if time_diff_abs <= 10:
                            logger.debug(
                                f"✅ Sesión #{ses.id} - diferencia mínima ({int(time_diff)}s), sin cambios"
                            )
                            continue

                        # Solo procesar si diferencia > 10 segundos
                        elif time_diff > 10:
                            calendar_wins = False
                            conflict_reason = (
                                f"app_significantly_newer_by_{int(time_diff)}s"
                            )
                        else:
                            calendar_wins = True
                            conflict_reason = (
                                f"calendar_significantly_newer_by_{int(-time_diff)}s"
                            )

                    except Exception as e:
                        logger.warning(
                            f"⚠️ Error calculando timestamps para sesión #{ses.id}: {e}"
                        )
                        calendar_wins = True
                        conflict_reason = "timestamp_error"
                else:
                    calendar_wins = True
                    conflict_reason = "no_timestamps"

                # Aplicar resolucion
                if calendar_wins:
                    logger.info(
                        f"🔄 CALENDAR WINS - Sesión #{ses.id} ({conflict_reason})"
                    )

                    is_valid, error_msg, warnings = validate_session_for_import(
                        start_dt, end_dt
                    )

                    if not is_valid:
                        # Recahzar update si es inválido
                        # Obtener nombres (manejar snapshots)
                        if ses.coach_id and ses.coach and ses.coach.user:
                            coach_name = ses.coach.user.name
                        else:
                            coach_name = ses.coach_name_snapshot or "Coach deleted"

                        if ses.player_id and ses.player and ses.player.user:
                            player_name = ses.player.user.name
                        else:
                            player_name = ses.player_name_snapshot or "Player deleted"

                        rejected_events.append(
                            {
                                "title": f"{coach_name} × {player_name}",
                                "date": start_dt.strftime("%d/%m/%Y"),
                                "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                                "reason": error_msg,
                                "suggestion": "Corregir horarios en Google Calendar",
                            }
                        )
                        logger.warning(
                            f"🚫 UPDATE RECHAZADO - Sesión #{ses.id}: {error_msg}"
                        )
                        continue  # No actualizar, saltar al siguiente evento

                    changed = False
                    changes = []

                    # Si hay warnings, agregar a lista
                    if warnings:
                        # Obtener nombres (manejar snapshots)
                        if ses.coach_id and ses.coach and ses.coach.user:
                            coach_name = ses.coach.user.name
                        else:
                            coach_name = ses.coach_name_snapshot or "Coach deleted"

                        if ses.player_id and ses.player and ses.player.user:
                            player_name = ses.player.user.name
                        else:
                            player_name = ses.player_name_snapshot or "Player deleted"

                        warning_events.append(
                            {
                                "title": f"{coach_name} × {player_name}",
                                "date": start_dt.strftime("%d/%m/%Y"),
                                "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                                "warnings": warnings,
                            }
                        )
                        logger.warning(
                            f"⚠️ SESIÓN ACTUALIZADA CON WARNINGS - #{ses.id}: {'; '.join(warnings)}"
                        )

                    # Aplicar cambios del calendario
                    if ses.status != status:
                        changes.append(f"status: {ses.status.value} → {status.value}")
                        ses.status = status
                        changed = True

                    db_start = ses.start_time.astimezone(dt.timezone.utc).replace(
                        microsecond=0
                    )
                    new_start = start_dt.astimezone(dt.timezone.utc).replace(
                        microsecond=0
                    )
                    if db_start != new_start:
                        changes.append(
                            f"start: {format_time_local(db_start)} → {format_time_local(new_start)}"
                        )
                        ses.start_time = start_dt
                        changed = True

                    db_end = ses.end_time.astimezone(dt.timezone.utc).replace(
                        microsecond=0
                    )
                    new_end = end_dt.astimezone(dt.timezone.utc).replace(microsecond=0)
                    if db_end != new_end:
                        changes.append(
                            f"end: {format_time_local(db_end)} → {format_time_local(new_end)}"
                        )
                        ses.end_time = end_dt
                        changed = True

                    new_notes = ev.get("description", "") or ""
                    if (ses.notes or "") != new_notes:
                        changes.append("notes")
                        ses.notes = new_notes if new_notes else None
                        changed = True

                    if changed:
                        update_session_tracking(ses)
                        logger.info(
                            f"📝 CALENDAR→BD Sesión #{ses.id}: {', '.join(changes)}"
                        )
                        db.add(ses)
                        updated += 1
                    else:
                        logger.debug(
                            f"✅ Sesión #{ses.id} sin cambios después de análisis"
                        )

                else:
                    # APP wins - actualizar Calendar desde BD
                    logger.info(f"🔄 APP WINS - Sesión #{ses.id} ({conflict_reason})")
                    # SKIP QUIRÚRGICO: Sesión #912 problemática que siempre causa timeout
                    if ses.id == 912:
                        logger.warning(f"⚠️ SKIP: Omitiendo sesión #{ses.id} (conocida problemática)")
                        continue
                    
                    logger.info(
                        f"📝 BD→CALENDAR: Forzando actualización de evento desde sesión #{ses.id}"
                    )

                    try:
                        ses.is_dirty = False
                        ses.last_sync_at = dt.datetime.now(dt.timezone.utc)
                        update_session_in_calendar_only(ses)
                        logger.info(f"✅ Evento actualizado en Calendar desde BD")
                    except Exception as e:
                        logger.error(f"❌ Error actualizando Calendar desde BD: {e}")
                        ses.is_dirty = True
                        db.add(ses)

            else:
                # Crear nueva sesion con validación
                logger.info(
                    f"🆕 Creando sesión nueva: {ev.get('summary', 'Sin título')}"
                )
                coach_id, player_id = guess_coach_player_ids(ev)

                if coach_id is None or player_id is None:
                    rejected_events.append(
                        {
                            "title": ev.get("summary", "Sin título"),
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "reason": "No se pudo identificar coach/player en el título",
                            "suggestion": "Verificar formato: 'Juan × María #C1 #P5'",
                        }
                    )
                    logger.warning(
                        f"⚠️ No se pudo mapear evento - coach_id: {coach_id}, player_id: {player_id}"
                    )
                    continue

                # Validar que coach y player exiten en bd
                coach_exists = (
                    db.query(Coach)
                    .options(joinedload(Coach.user))
                    .filter(Coach.coach_id == coach_id)
                    .first()
                )
                player_exists = (
                    db.query(Player)
                    .options(joinedload(Player.user))
                    .filter(Player.player_id == player_id)
                    .first()
                )

                if not coach_exists:
                    rejected_events.append(
                        {
                            "title": ev.get("summary", "Sin título"),
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "reason": f"Coach ID {coach_id} no existe en la base de datos",
                            "suggestion": "Verificar que el coach esté registrado en la aplicación",
                        }
                    )
                    logger.warning(
                        f"⚠️ Coach ID {coach_id} no existe en BD - ignorando evento"
                    )
                    continue

                if not player_exists:
                    rejected_events.append(
                        {
                            "title": ev.get("summary", "Sin título"),
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "reason": f"Player ID {player_id} no existe en la base de datos",
                            "suggestion": "Verificar que el player esté registrado en la aplicación",
                        }
                    )
                    logger.warning(
                        f"⚠️ Player ID {player_id} no existe en BD - ignorando evento"
                    )
                    continue

                # VAalidacion flexible con feedback al usuario
                is_valid, error_msg, warnings = validate_session_for_import(
                    start_dt, end_dt
                )

                if not is_valid:
                    # Rechazado - feedback al usuario
                    rejected_events.append(
                        {
                            "title": ev.get("summary", "Sin título"),
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "reason": error_msg,
                            "suggestion": "Corregir horarios en Google Calendar y ejecutar sync manual",
                        }
                    )
                    logger.error(
                        f"❌ EVENTO RECHAZADO - {ev.get('summary', 'Sin título')}: {error_msg}"
                    )
                    continue

                # Verificar si tiene warnings
                if warnings:
                    warning_events.append(
                        {
                            "title": ev.get("summary", "Sin título"),
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "warnings": warnings,
                        }
                    )
                    logger.warning(
                        f"⚠️ EVENTO CON WARNINGS - {ev.get('summary', 'Sin título')}: {'; '.join(warnings)}"
                    )
                else:
                    logger.info(
                        f"✅ Mapeado y validado - Coach ID: {coach_id}, Player ID: {player_id}"
                    )

                # Obtener nombres para snapshots
                coach_name_snapshot = (
                    coach_exists.user.name
                    if coach_exists and coach_exists.user
                    else f"Coach {coach_id}"
                )
                player_name_snapshot = (
                    player_exists.user.name
                    if player_exists and player_exists.user
                    else f"Player {player_id}"
                )

                new_session = Session(
                    coach_id=coach_id,
                    player_id=player_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    status=status,
                    notes=ev.get("description"),
                    coach_name_snapshot=coach_name_snapshot,
                    player_name_snapshot=player_name_snapshot,
                    calendar_event_id=ev_id,
                    source="calendar",
                    version=1,
                )

                db.add(new_session)
                db.flush()

                # Actualizar formato del evento en Calendar
                try:
                    patch_event_after_import(new_session, ev_id)
                    logger.debug(f"🔧 Evento {ev_id[:8]}... actualizado")
                except Exception as e:
                    logger.error(f"❌ Error actualizando evento en Calendar: {e}")

                imported += 1

        # Detectar eliminaciones
        logger.info("🗑️ Verificando eventos eliminados...")

        # Sesiones en ventana que DEBERÍAN tener eventos correspondientes
        sessions_in_window = (
            db.query(Session)
            .filter(
                Session.calendar_event_id != None,
                Session.start_time >= win_start,
                Session.start_time <= win_end,
            )
            .all()
        )

        # Crear dict de sesiones en la ventana
        window_sessions = {s.calendar_event_id: s for s in sessions_in_window}

        # Candidatos: event_ids de BD que no aparecieron en la búsqueda de Calendar
        elimination_candidates = [
            ev_id for ev_id in window_sessions.keys() if ev_id not in seen_ev_ids
        ]

        logger.info(f"🔍 Sesiones en ventana: {len(window_sessions)}")
        logger.info(f"🔍 Candidatos para eliminación: {len(elimination_candidates)}")

        # Si no aparece en la búsqueda de la ventana = eliminado
        if elimination_candidates:
            for ev_id in elimination_candidates:
                ses = window_sessions[ev_id]

                logger.info(
                    f"🗑️ ELIMINANDO sesión #{ses.id} - evento {(ev_id[:8] if ev_id else 'N/A')}... no encontrado en ventana"
                )
                db.delete(ses)
                deleted += 1

        if deleted == 0:
            logger.info("✅ No hay eventos para eliminar")

        # Commit final
        db.commit()

        elapsed_time = time.time() - start_time
        events_per_second = len(events) / elapsed_time if elapsed_time > 0 else 0

        logger.info(
            f"✅ SYNC COMPLETADA en {elapsed_time:.2f}s ({events_per_second:.1f} eventos/seg)"
        )
        logger.info(
            f"📊 Resultados: {imported} importadas, {updated} actualizadas, {deleted} eliminadas"
        )

        # Log resumen de problemas
        if rejected_events:
            logger.warning(
                f"🚫 {len(rejected_events)} eventos rechazados por problemas críticos"
            )
        if warning_events:
            logger.warning(
                f"⚠️ {len(warning_events)} eventos importados con advertencias"
            )

        return imported, updated, deleted, rejected_events, warning_events

    except Exception as e:
        # Logging de errores
        if "403" in str(e):
            logger.error(
                "❌ ERROR 403: Sin permisos para Google Calendar - verificar API keys"
            )
        elif "404" in str(e):
            logger.error(
                "❌ ERROR 404: Calendario no encontrado - verificar CALENDAR_ID"
            )
        elif "JSON" in str(e) or "Expecting property name" in str(e):
            logger.error(
                "❌ ERROR AUTH: Credenciales inválidas - verificar google_service_account.json"
            )
        else:
            logger.error(f"❌ ERROR sincronización: {e}")

        db.rollback()
        raise
    finally:
        db.close()


def sync_calendar_to_db() -> Tuple[int, int, int]:
    """Función simplificada que solo devuelve estadísticas básicas (para auto-sync)."""
    imported, updated, deleted, rejected_events, warning_events = (
        sync_calendar_to_db_with_feedback()
    )

    # Solo loggar problemas pero no devolver las listas (para auto-sync simple)
    if rejected_events:
        logger.warning(f"🚫 Auto-sync rechazó {len(rejected_events)} eventos")
    if warning_events:
        logger.warning(
            f"⚠️ Auto-sync importó {len(warning_events)} eventos con advertencias"
        )

    return imported, updated, deleted


def sync_db_to_calendar() -> Tuple[int, int]:
    """
    Sincroniza sesiones de BD hacia Google Calendar.
    Ahora respeta correctamente session_needs_update() y no actualiza innecesariamente.

    Returns:
        Tuple (pushed, updated)
    """

    with SessionController() as controller:
        db = controller.db
        pushed = updated = skipped = 0

        for ses in db.query(Session).all():
            if not ses.calendar_event_id:
                # NUEVO: Verificar si ya existe evento duplicado antes de crear
                existing_event_id = controller._find_existing_calendar_event(ses)
                if existing_event_id:
                    # Ya existe evento para esta sesión → vincular
                    logger.info(
                        f"🔗 VINCULANDO: Sesión #{ses.id} ya tiene evento {existing_event_id[:8]}..."
                    )
                    ses.calendar_event_id = existing_event_id
                    # Actualizar tracking para sincronizar hashes
                    from controllers.calendar_utils import update_session_tracking

                    update_session_tracking(ses)
                    db.add(ses)
                    pushed += 1  # Contarlo como "pushed" aunque sea vincular
                else:
                    # Sin event_id y no existe → crear nuevo
                    success = controller._push_session_to_calendar(ses)
                    if success:
                        pushed += 1
                        logger.info(f"📤 NUEVO: Sesión #{ses.id} creada en Calendar")
            else:
                # Verificar si necesita actualizacion
                if session_needs_update(ses):
                    # Solo actualizar si realmente hay cambios
                    success = controller._update_session_in_calendar(ses)
                    if success:
                        updated += 1
                        logger.info(
                            f"🔄 ACTUALIZADA: Sesión #{ses.id} actualizada en Calendar"
                        )
                    else:
                        logger.warning(
                            f"❌ FALLO: Sesión #{ses.id} falló al actualizar"
                        )
                else:
                    skipped += 1
                    logger.debug(f"⏭️ OMITIDA: Sesión #{ses.id} sin cambios")

        # Log detallado
        total_processed = pushed + updated + skipped
        logger.info(f"📊 Push BD→Calendar completado:")
        logger.info(f"   📤 {pushed} sesiones NUEVAS creadas")
        logger.info(f"   🔄 {updated} sesiones ACTUALIZADAS")
        logger.info(f"   ⏭️ {skipped} sesiones OMITIDAS (sin cambios)")
        logger.info(f"   📋 {total_processed} sesiones procesadas")

        if updated > 10:
            logger.warning(
                f"⚠️ ADVERTENCIA: {updated} sesiones actualizadas - investigar por qué necesitan update"
            )

        return pushed, updated


def patch_color(event_id: str, status: SessionStatus):
    """Actualiza solo el color de un evento en Calendar."""
    COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()}

    calendar().events().patch(
        calendarId=CAL_ID, eventId=event_id, body={"colorId": COLOR[status.value]}
    ).execute()
