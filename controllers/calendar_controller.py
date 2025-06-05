import streamlit as st
import datetime as dt
import os
import re 
import logging
import time
from unidecode import unidecode
import hashlib
from zoneinfo import ZoneInfo
from googleapiclient.errors import HttpError
from sqlalchemy import func
from sqlalchemy.orm import object_session, Session as AlchSession
from .google_client import calendar
from googleapiclient.errors import HttpError
from models import Session, SessionStatus, Coach, Player, User        
from controllers.db import get_db_session
from common.validation import validate_session_for_import


from config import CALENDAR_COLORS
COLOR = {k: v["google"] for k, v in CALENDAR_COLORS.items()} 
CAL_ID = os.getenv("CALENDAR_ID")
LOCAL_TZ = ZoneInfo("Europe/Madrid")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler para mostrar en streamlit si no existe
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def _format_time_local(dt_obj):
    """Convierte datetime UTC a hora local Madrid para logging legible"""
    if dt_obj is None:
        return "None"
        
    # Asegurar que tiene timezone info
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
    
    # Convertir a hora de Madrid
    local_time = dt_obj.astimezone(LOCAL_TZ)
    return local_time.strftime('%H:%M')

def _normalize_datetime_for_hash(dt_obj) -> str:
    """
    Normaliza datetime para hash: convierte a UTC y quita timezone info
    MEJORADO: Maneja correctamente datetime naive desde timezone local
    """
    if dt_obj is None:
        return ""
    
    # Si es string, convertir a datetime primero
    if isinstance(dt_obj, str):
        try:
            dt_obj = dt.datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
        except:
            return dt_obj  # Si falla, devolver como está
    
    # ================================================================
    # LÓGICA MEJORADA PARA DATETIME NAIVE
    # ================================================================
    
    if dt_obj.tzinfo is None:
        # OPCIÓN 1: Asumir que datetime naive es en timezone local (Madrid)
        # Esto es más probable para sesiones creadas desde la app
        try:
            local_tz = ZoneInfo("Europe/Madrid")  # +01:00 en invierno, +02:00 en verano
            dt_obj = dt_obj.replace(tzinfo=local_tz)
            logger.debug(f"🌍 Datetime naive convertido a Madrid timezone: {dt_obj}")
        except:
            # Si falla ZoneInfo, usar offset fijo +02:00 (horario de verano típico)
            dt_obj = dt_obj.replace(tzinfo=dt.timezone(dt.timedelta(hours=2)))
            logger.debug(f"🌍 Datetime naive convertido a +02:00: {dt_obj}")
    
    # Convertir a UTC y quitar timezone info para consistencia
    utc_naive = dt_obj.astimezone(dt.timezone.utc).replace(tzinfo=None)
    
    # Devolver formato ISO sin microsegundos
    result = utc_naive.replace(microsecond=0).isoformat()
    logger.debug(f"🔧 Normalización final: {dt_obj} → {result}")
    return result

def _calculate_session_hash(session: Session) -> str:
    """Calcula hash MD5 basado en datos importantes de la sesión CON FECHAS NORMALIZADAS."""
    try:
        # Normalizar fechas
        start_normalized = _normalize_datetime_for_hash(session.start_time)
        end_normalized = _normalize_datetime_for_hash(session.end_time)
        
        data = "|".join([
            str(session.coach_id),
            str(session.player_id), 
            start_normalized,
            end_normalized,
            session.status.value,
            session.notes or ""
        ])
        
        hash_result = hashlib.md5(data.encode('utf-8')).hexdigest()
        logger.debug(f"🔧 Session hash data: '{data}' → {hash_result[:8]}...")
        return hash_result
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando hash sesión #{session.id}: {e}")
        return ""

def _calculate_event_hash(ev: dict) -> str:
    """Calcula hash MD5 basado en datos importantes del evento CON FECHAS NORMALIZADAS."""
    try:
        def _to_dt_local(iso: str) -> dt.datetime:
            return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        
        # Obtener fechas del evento y normalizarlas
        start_dt = _to_dt_local(ev["start"]["dateTime"])
        end_dt = _to_dt_local(ev["end"]["dateTime"])
        
        start_normalized = _normalize_datetime_for_hash(start_dt)
        end_normalized = _normalize_datetime_for_hash(end_dt)
        
        status = _status_from_color(ev.get("colorId", "9"))
        
        props = ev.get("extendedProperties", {}).get("private", {})
        coach_id = props.get("coach_id", "")
        player_id = props.get("player_id", "")
        
        data = "|".join([
            str(coach_id),
            str(player_id),
            start_normalized,
            end_normalized,
            status.value,
            ev.get("description", "") or ""
        ])
        
        hash_result = hashlib.md5(data.encode('utf-8')).hexdigest()
        logger.debug(f"🔧 Event hash data: '{data}' → {hash_result[:8]}...")
        return hash_result
        
    except Exception as e:
        logger.warning(f"⚠️ Error calculando hash evento: {e}")
        return ""

# BONUS: Función para verificar el fix
def test_hash_normalization():
    """Test para verificar que la normalización funciona"""
    from models import Session
    from controllers.db import get_db_session
    
    db = get_db_session()
    session = db.get(Session, 318)  # Usar sesión problemática
    
    if session and session.calendar_event_id:
        print("🧪 TESTING HASH NORMALIZATION")
        print("="*50)
        
        # Hash de sesión
        session_hash = _calculate_session_hash(session)
        print(f"Session hash (normalizado): {session_hash}")
        
        # Obtener evento y calcular hash
        try:
            import os
            from .google_client import calendar
            CAL_ID = os.getenv("CALENDAR_ID")
            event = calendar().events().get(
                calendarId=CAL_ID,
                eventId=session.calendar_event_id
            ).execute()
            
            event_hash = _calculate_event_hash(event)
            print(f"Event hash (normalizado):   {event_hash}")
            
            if session_hash == event_hash:
                print("✅ SUCCESS: Hashes ahora coinciden!")
            else:
                print("❌ FAIL: Hashes siguen siendo diferentes")
                
        except Exception as e:
            print(f"❌ Error obteniendo evento: {e}")
    
    db.close()

def _update_session_tracking(session: Session):
    """Actualiza campos de tracking después de cambios."""
    try:
        session.sync_hash = _calculate_session_hash(session)
        session.updated_at = dt.datetime.now(dt.timezone.utc)
        session.last_sync_at = dt.datetime.now(dt.timezone.utc)
        session.is_dirty = False
        session.version = (session.version or 0) + 1
        
        logger.debug(f"📝 Tracking actualizado: Sesión #{session.id} v{session.version}")
    except Exception as e:
        logger.warning(f"⚠️ Error actualizando tracking sesión #{session.id}: {e}")

def _update_session_in_calendar_only(session: Session):
    """Actualiza evento en Calendar sin tocar la sesión BD actual."""
    if not session.calendar_event_id:
        logger.warning(f"⚠️ Sesión #{session.id} sin event_id")
        return

    try:
        body = _build_body(session)
        _service().events().patch(
            calendarId=CAL_ID,
            eventId=session.calendar_event_id,
            body=body
        ).execute()
        logger.debug(f"📤 Evento {session.calendar_event_id[:8]}... actualizado desde BD")
        
    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(f"⚠️ Evento {session.calendar_event_id[:8]}... no existe en Calendar")
        else:
            logger.error(f"❌ Error actualizando evento en Calendar: {e}")
            raise

def _db():
    return get_db_session()

def _service():
    return calendar()

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
    
d_safe_int = lambda x: int(x) if x and str(x).isdigit() else None

def _normalize(text: str) -> str:
    """Pasa a minúsculas, quita tildes y unifica espacios."""
    return re.sub(r"\s+", " ", unidecode(text or "").strip().lower())

def _extract_id(text: str, pattern: str):
    """Busca con regex y devuelve el grupo 1 como int, o None."""
    m = re.search(pattern, text, flags=re.I)
    return _safe_int(m.group(1)) if m else None

def _find_unique(model, name_norm: str):
    """
    Trae todos los registros del modelo (Coach o Player),
    normaliza user.name y devuelve el único que coincide con name_norm.
    Si hay 0 o >1, devuelve None.
    """
    db = get_db_session()
    rows = (
        db.query(model)
          .join(User)
          .filter(User.is_active)
          .all()
    )
    matches = [r for r in rows if _normalize(r.user.name) == name_norm]
    return matches[0] if len(matches) == 1 else None

# —————————————————————————————————————————————————————————————————————
# Función mixta para sacar coach_id y player_id de un evento de Google
# —————————————————————————————————————————————————————————————————————
def _guess_ids(ev):
    """
    ESTRATEGIA HÍBRIDA INTELIGENTE:
    1) Extended properties (automático)
    2) Parsing híbrido: nombres + IDs opcionales  
    3) Solo nombres (fuzzy)
    4) Solo IDs (#C #P)
    """
    props = ev.get("extendedProperties", {}).get("private", {})
    
    # 1) Extended properties (solo si válidos)
    cid = _safe_int(props.get("coach_id"))
    pid = _safe_int(props.get("player_id"))
    if cid and pid and cid < 100 and pid < 100:
        return cid, pid

    summary = ev.get("summary", "") or ""
    
    # 2) PARSING HÍBRIDO: nombres + IDs opcionales
    # Limpiar prefijo "Sesión:" / "Session:"
    summary_clean = re.sub(r'^(?:sesión|session)[:\-]\s*', '', summary, flags=re.IGNORECASE)
    
    # Buscar patrón: [algo] × [algo] o [algo] x [algo]
    match = re.search(r"(.+?)\s*[×x]\s*(.+)", summary_clean, re.IGNORECASE)
    
    if match:
        left_part = match.group(1).strip()   # Lado coach
        right_part = match.group(2).strip()  # Lado player
        
        coach_id = player_id = None
        
        # ANALIZAR LADO COACH (izquierda)
        coach_id_match = re.search(r"#[Cc](\d+)", left_part)
        if coach_id_match:
            # Hay ID explícito → usarlo
            coach_id = int(coach_id_match.group(1))
        else:
            # No hay ID → buscar por nombre
            coach_name = left_part.strip()
            coach_name_norm = _normalize(coach_name)
            coach_obj = _find_unique(Coach, coach_name_norm)
            if coach_obj:
                coach_id = coach_obj.coach_id
        
        # ANALIZAR LADO PLAYER (derecha)  
        player_id_match = re.search(r"#[Pp](\d+)", right_part)
        if player_id_match:
            # Hay ID explícito → usarlo
            player_id = int(player_id_match.group(1))
        else:
            # No hay ID → buscar por nombre
            player_name = right_part.strip()
            player_name_norm = _normalize(player_name)
            player_obj = _find_unique(Player, player_name_norm)
            if player_obj:
                player_id = player_obj.player_id
        
        # Si encontramos ambos, devolver
        if coach_id and player_id:
            return coach_id, player_id
    
    # 3) FALLBACK: Solo IDs tradicionales #C #P (anywhere en título)
    cid = (_extract_id(summary, r"#C(\d+)") or
           _extract_id(summary, r"Coach[#\s]*(\d+)"))
    pid = (_extract_id(summary, r"#P(\d+)") or
           _extract_id(summary, r"Player[#\s]*(\d+)"))
    if cid and pid:
        return cid, pid

    return None, None

# ---------- DB → Calendar ----------
def push_session(session: Session, db: AlchSession | None = None):
    """Crea evento en Google Calendar con manejo correcto de sesiones."""
    if db is None:
        db = object_session(session) or get_db_session()
    
    if object_session(session) != db:
        session = db.merge(session)

    # Actualizar tracking antes de enviar
    _update_session_tracking(session)
    session.source = "app"
    
    body = _build_body(session)
    ev = _service().events().insert(
        calendarId=CAL_ID, body=body).execute()

    session.calendar_event_id = ev["id"]
    session.is_dirty = False
    
    if db != object_session(session):
        db.add(session)
        db.commit()
        
        # ✅ FIX: Solo actualizar timestamp después de SUCCESS
        session.updated_at = dt.datetime.now(dt.timezone.utc)
        session.last_sync_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        db.refresh(session)
    
    logger.info(f"📤 Sesión #{session.id} creada en Calendar (evento {ev['id'][:8]}...)")

def update_session(session: Session):
    """Actualiza evento existente SOLO SI HAY CAMBIOS REALES."""
    db = object_session(session) or get_db_session()
    
    if object_session(session) != db:
        session = db.merge(session)
    
    if not session.calendar_event_id:
        logger.warning(f"⚠️ Sesión #{session.id} sin event_id - usando push_session")
        return push_session(session, db)

    # Verificar si realmente hay cambios antes de actualizar
    if not _session_has_real_changes(session):
        logger.debug(f"⏭️ Sesión #{session.id} - sin cambios reales, skip update")

        return
    # Logging más específico sobre el tipo de actualización
    logger.info(f"🔄 MANUAL UPDATE - Sesión #{session.id} (cambios locales)")
    
    # Actualizar tracking antes de enviar
    _update_session_tracking(session)
    
    body = _build_body(session)
    try:
        _service().events().patch(
            calendarId=CAL_ID,
            eventId=session.calendar_event_id,
            body=body
        ).execute()

        # Solo actualizar timestamp después de SUCCESS
        session.updated_at = dt.datetime.now(dt.timezone.utc)
        session.last_sync_at = dt.datetime.now(dt.timezone.utc)
        session.is_dirty = False
        
        logger.info(f"📤 Sesión #{session.id} actualizada en Calendar")
        
    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(f"⚠️ Evento {session.calendar_event_id[:8]}... no existe - recreando")
            session.calendar_event_id = None
            push_session(session, db)
        else:
            session.is_dirty = True
            logger.error(f"❌ Error actualizando evento: {e}")
            raise
    
    if object_session(session) is None:
        db.add(session)
        db.commit()

#  BORRAR una sesión
def delete_session(session: Session):
    """
    Borra el evento de Calendar si existe y devuelve True/False
    según se haya eliminado o no.
    """
    if not session.calendar_event_id:
        return False
    try:
        _service().events().delete(
            calendarId=CAL_ID,
            eventId=session.calendar_event_id
        ).execute()
        return True
    except HttpError as e:                 # ya no existe → ignoramos
        if e.resp.status != 404:
            raise
        return False

# --------------------------------------------------------------------------
#  UTILIDAD compartida
def _build_body(session: Session) -> dict:
    """Devuelve el diccionario body que Calendar API espera."""
    return {
        "summary": (
            f"Session: {session.coach.user.name} × {session.player.user.name} "
            f"#C{session.coach_id} #P{session.player_id}"
        ),
        "description": session.notes or "",
        "start": {"dateTime": session.start_time.astimezone(dt.timezone.utc).isoformat()},
        "end":   {"dateTime": session.end_time.astimezone(dt.timezone.utc).isoformat()},
        "colorId": COLOR[session.status.value],
        "extendedProperties": {
            "private": {
                "session_id": str(session.id),
                "coach_id":   str(session.coach_id),
                "player_id":  str(session.player_id),
            }
        },
    }

def patch_color(event_id: str, status: SessionStatus):
    _service().events().patch(
        calendarId=CAL_ID, eventId=event_id,
        body={"colorId": COLOR[status.value]}
    ).execute()

def patch_event_after_import(session: Session, event_id: str):
    """
    Parcha un evento importado: añade IDs y formatea el título.
    OPTIMIZADO: Solo si realmente es necesario.
    """
    try:
        # Verificar si el evento ya tiene los datos correctos
        current_event = _service().events().get(calendarId=CAL_ID, eventId=event_id).execute()
        
        props = current_event.get("extendedProperties", {}).get("private", {})
        session_id_in_event = props.get("session_id")
        
        # Si ya tiene el session_id correcto, no hacer nada
        if session_id_in_event == str(session.id):
            logger.debug(f"✅ Evento {event_id[:8]}... ya tiene datos correctos")
            return
        
        # Solo patchear si realmente es necesario
        db = get_db_session()
        try:
            coach_name = db.query(User.name).join(Coach).filter(Coach.coach_id == session.coach_id).scalar()
            player_name = db.query(User.name).join(Player).filter(Player.player_id == session.player_id).scalar()

            patch_body = {
                "summary": f"Sesión: {coach_name} × {player_name}  #C{session.coach_id} #P{session.player_id}",
                "extendedProperties": {
                    "private": {
                        "session_id": str(session.id),
                        "coach_id": str(session.coach_id),
                        "player_id": str(session.player_id),
                    }
                }
            }

            _service().events().patch(
                calendarId=CAL_ID,
                eventId=event_id,
                body=patch_body
            ).execute()
            
            logger.info(f"🔧 Evento {event_id[:8]}... actualizado correctamente")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error actualizando evento {event_id[:8]}...: {e}")

# ---------- DB → Calendar ----------   

def _session_has_real_changes(session: Session) -> bool:
    """
    Verifica si una sesión tiene cambios REALES que justifiquen update
    """
    # 1. Si está marcada como dirty → hay cambios
    if hasattr(session, 'is_dirty') and session.is_dirty:
        logger.debug(f"🔄 Sesión #{session.id} marcada como dirty")
        return True
    
    # 2. Si no tiene hash → primera vez
    if not session.sync_hash:
        logger.debug(f"🔄 Sesión #{session.id} sin hash - primera sincronización")
        return True
    
    # 3. Comparar hash actual vs. guardado
    current_hash = _calculate_session_hash(session)
    
    if session.sync_hash != current_hash:
        logger.debug(f"🔄 Sesión #{session.id} hash cambió: {session.sync_hash[:8]}... → {current_hash[:8]}...")
        return True
    
    # 4. Sin cambios reales
    logger.debug(f"✅ Sesión #{session.id} - sin cambios reales")
    return False

def sync_db_to_calendar():
    """
    VERSIÓN OPTIMIZADA: Solo actualiza sesiones que realmente han cambiado
    """
    db = get_db_session()
    pushed = updated = skipped = 0

    for ses in db.query(Session).all():
        if not ses.calendar_event_id:
            # Sin event_id → crear nuevo
            push_session(ses)
            pushed += 1
        elif _session_needs_update(ses):
            # Verificar si necesita actualización
            update_session(ses)
            updated += 1
        else:
            skipped += 1
            logger.debug(f"⏭️ Sesión #{ses.id} - sin cambios, skip update")

    logger.info(f"📊 Push completado: {pushed} creadas, {updated} actualizadas, {skipped} omitidas")
    return pushed, updated

def _session_needs_update(session: Session) -> bool:
    """Versión simple - Solo actualizar si está dirty o no tiene hash"""
    # 1. Si está dirty → actualizar
    if hasattr(session, 'is_dirty') and session.is_dirty:
        return True
    
    # 2. Si no tiene hash → actualizar
    if not session.sync_hash:
        return True
        
    # 3. Verificar cambios en hash
    current_hash = _calculate_session_hash(session)
    has_changes = session.sync_hash != current_hash
    
    if has_changes:
        logger.debug(f"🔄 Sesión #{session.id} - cambios detectados en hash")
    
    return has_changes

# ---------- Calendar → DB ----------

def sync_calendar_to_db_with_feedback():
    """Sincroniza eventos de Google Calendar hacia la base de datos con logging detallado."""
    start_time = time.time()
    logger.info("🔄 INICIANDO sincronización Calendar → BD")
    
    svc = _service()
    db = get_db_session()

    rejected_events = []  # Lista de eventos rechazados
    warning_events = []   # Lista de eventos con warnings
    
    try:
        imported = updated = deleted = 0
        seen_ev_ids: set[str] = set()

        now = dt.datetime.now(dt.timezone.utc)
        win_start = now - dt.timedelta(days=15)
        win_end   = now + dt.timedelta(days=30)
        
        logger.info(f"📅 Ventana de sincronización: {win_start.date()} a {win_end.date()}")

        # Obtener eventos de Google Calendar
        logger.info("📡 Obteniendo eventos de Google Calendar...")
        events_response = svc.events().list(
            calendarId=CAL_ID,
            timeMin=win_start.isoformat(),
            timeMax=win_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = events_response.get("items", [])
        logger.info(f"📋 Encontrados {len(events)} eventos en Google Calendar")

        def _to_dt(iso: str) -> dt.datetime:
            return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))

        # Cargar todas las sesiones con calendar_event_id ya guardado
        logger.info("🗄️ Cargando sesiones existentes de la BD...")
        db_sessions = {
            s.calendar_event_id: s
            for s in db.query(Session)
                        .filter(Session.calendar_event_id != None)
                        .all()
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
            status = _status_from_color(ev.get("colorId", "9"))
            
            
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
                coach_id, player_id = _guess_ids(ev)
                if coach_id and player_id:
                    # Buscar sesión sin event_id que coincida en fecha/coach/player
                    potential_matches = db.query(Session).filter(
                        Session.coach_id == coach_id,
                        Session.player_id == player_id,
                        Session.calendar_event_id == None,
                        func.date(Session.start_time) == start_dt.date()
                    ).all()
                    
                    if potential_matches:
                        ses = potential_matches[0]
                        ses.calendar_event_id = ev_id  # Vincular evento
                        logger.info(f"🔗 MATCH FUZZY: Sesión #{ses.id} vinculada al evento {ev_id[:8]}...")
                        db.add(ses)
                        db.flush()

            if ses:
                
                # Hash first - Verificar si ya tiene un hash
                
                # 1. Verificar si event_id coincide
                if ses.calendar_event_id != ev_id:
                    logger.debug(f"🔗 Actualizando event_id: {ses.calendar_event_id} → {ev_id}")
                    ses.calendar_event_id = ev_id
                    db.add(ses)
                    db.flush()

                # 2. HASH COMPARISON - Prioridad máxima
                current_hash = ses.sync_hash or ""
                
                # Si no tiene hash, calcularlo ahora (sesión antigua)
                if not current_hash:
                    current_hash = _calculate_session_hash(ses)
                    ses.sync_hash = current_hash
                    logger.debug(f"🔧 Hash inicial calculado para sesión #{ses.id}")

                event_hash = _calculate_event_hash(ev)
                
                logger.debug(f"🔍 Hash check Sesión #{ses.id}: BD='{current_hash[:8]}...' vs Event='{event_hash[:8]}...'")
                
                # 3. Si hashes coinciden → NO HAY CAMBIOS REALES
                if current_hash == event_hash:
                    logger.debug(f"✅ Sesión #{ses.id} - hashes coinciden, sin cambios")
                    continue
                
                # 4. HASHES DIFERENTES → Hay cambios reales, decidir quién gana
                
                # 4a. Verificar si sesión está marcada como dirty (cambios locales pendientes)
                if hasattr(ses, 'is_dirty') and ses.is_dirty:
                    # Sesión local tiene cambios pendientes → APP WINS
                    logger.info(f"🔄 APP WINS - Sesión #{ses.id} ({conflict_reason})")
                    logger.info(f"📝 BD→CALENDAR: Forzando actualización de evento desde sesión #{ses.id}")
                    
                    try:
                        ses.is_dirty = False
                        ses.last_sync_at = dt.datetime.now(dt.timezone.utc)
                        _update_session_in_calendar_only(ses)
                        logger.info(f"✅ Evento actualizado en Calendar desde BD (APP WINS)")  # 🔧 AGREGAR ESTA LÍNEA
                    except Exception as e:
                        logger.error(f"❌ Error actualizando Calendar desde BD: {e}")
                        ses.is_dirty = True
                        db.add(ses)

                    continue
                
                # 4b. Análisis de timestamps (solo como tiebreaker)
                event_updated_str = ev.get("updated") or ev.get("created") or ""
                event_updated = None
                session_updated = ses.updated_at or ses.created_at
                
                calendar_wins = True  # Default: Calendar wins
                conflict_reason = "hash_different_calendar_default"
                
                if event_updated_str and session_updated:
                    try:
                        event_updated = dt.datetime.fromisoformat(event_updated_str.replace("Z", "+00:00"))
                        if event_updated.tzinfo is None:
                            event_updated = event_updated.replace(tzinfo=dt.timezone.utc)
                        
                        if session_updated and session_updated.tzinfo is None:
                            session_updated = session_updated.replace(tzinfo=dt.timezone.utc)
                        
                        time_diff = (session_updated - event_updated).total_seconds()
                        time_diff_abs = abs(time_diff)

                        # Solo usar timestamps para DIFERENCIAS SIGNIFICATIVAS (>10 segundos)
                        if time_diff_abs <= 10:  
                            
                            logger.debug(f"✅ Sesión #{ses.id} - diferencia mínima ({int(time_diff)}s), sin cambios")
                            continue  
                            
                        # Solo procesar si diferencia > 10 segundos    
                        elif time_diff > 10:  
                            calendar_wins = False
                            conflict_reason = f"app_significantly_newer_by_{int(time_diff)}s"
                        else:
                            calendar_wins = True
                            conflict_reason = f"calendar_significantly_newer_by_{int(-time_diff)}s"
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Error calculando timestamps para sesión #{ses.id}: {e}")
                        # Si hay error, usar estrategia por defecto
                        calendar_wins = True
                        conflict_reason = "timestamp_error"
                else:
                    # Si no hay timestamps, usar estrategia por defecto  
                    calendar_wins = True
                    conflict_reason = "no_timestamps"
                    
                # 5. APLICAR RESOLUCIÓN
                if calendar_wins:
                    logger.info(f"🔄 CALENDAR WINS - Sesión #{ses.id} ({conflict_reason})")
                    
                    is_valid, error_msg, warnings = validate_session_for_import(start_dt, end_dt)
    
                    if not is_valid:
                        # RECHAZAR update si es inválido
                        rejected_events.append({
                            "title": f"{ses.coach.user.name} × {ses.player.user.name}",
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "reason": error_msg,
                            "suggestion": "Corregir horarios en Google Calendar"
                        })
                        logger.warning(f"🚫 UPDATE RECHAZADO - Sesión #{ses.id}: {error_msg}")
                        continue  # No actualizar, saltar al siguiente evento
                    
                    # Si hay warnings, agregar a lista
                    if warnings:
                        warning_events.append({
                            "title": f"{ses.coach.user.name} × {ses.player.user.name}",
                            "date": start_dt.strftime("%d/%m/%Y"),
                            "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                            "warnings": warnings
                        })

                    changed = False
                    changes = []
                    
                    # Aplicar cambios del calendario
                    if ses.status != status:
                        changes.append(f"status: {ses.status.value} → {status.value}")
                        ses.status = status
                        changed = True

                    db_start = ses.start_time.astimezone(dt.timezone.utc).replace(microsecond=0)
                    new_start = start_dt.astimezone(dt.timezone.utc).replace(microsecond=0)
                    if db_start != new_start:
                        changes.append(f"start: {_format_time_local(db_start)} → {_format_time_local(new_start)}")
                        ses.start_time = start_dt
                        changed = True

                    db_end = ses.end_time.astimezone(dt.timezone.utc).replace(microsecond=0)
                    new_end = end_dt.astimezone(dt.timezone.utc).replace(microsecond=0)
                    if db_end != new_end:
                        changes.append(f"end: {_format_time_local(db_end)} → {_format_time_local(new_end)}")
                        ses.end_time = end_dt
                        changed = True
                    
                    new_notes = ev.get("description", "") or ""
                    if (ses.notes or "") != new_notes:
                        changes.append("notes")
                        ses.notes = new_notes if new_notes else None
                        changed = True

                    if changed:
                        _update_session_tracking(ses)
                        logger.info(f"📝 CALENDAR→BD Sesión #{ses.id}: {', '.join(changes)}")
                        db.add(ses)
                        updated += 1
                    else:
                        logger.debug(f"✅ Sesión #{ses.id} sin cambios después de análisis")
                        
                else:
                    # APP WINS - actualizar Calendar desde BD
                    logger.info(f"🔄 APP WINS - Sesión #{ses.id} ({conflict_reason})")
                    logger.info(f"📝 BD→CALENDAR: Forzando actualización de evento desde sesión #{ses.id}")
                    
                    try:
                        ses.is_dirty = False
                        ses.last_sync_at = dt.datetime.now(dt.timezone.utc)
                        _update_session_in_calendar_only(ses)
                        logger.info(f"✅ Evento actualizado en Calendar desde BD")
                    except Exception as e:
                        logger.error(f"❌ Error actualizando Calendar desde BD: {e}")
                        ses.is_dirty = True
                        db.add(ses)
                    
            else:
                # CREAR NUEVA SESIÓN CON VALIDACIÓN
                logger.info(f"🆕 Creando sesión nueva: {ev.get('summary', 'Sin título')}")
                coach_id, player_id = _guess_ids(ev)
                
                if coach_id is None or player_id is None:
                    rejected_events.append({
                        "title": ev.get("summary", "Sin título"),
                        "date": start_dt.strftime("%d/%m/%Y"),
                        "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                        "reason": "No se pudo identificar coach/player en el título",
                        "suggestion": "Verificar formato: 'Juan × María #C1 #P5'"
                    })
                    logger.warning(f"⚠️ No se pudo mapear evento - coach_id: {coach_id}, player_id: {player_id}")
                    continue

                # VALIDAR QUE COACH Y PLAYER EXISTEN EN BD
                coach_exists = db.query(Coach).filter(Coach.coach_id == coach_id).first()
                player_exists = db.query(Player).filter(Player.player_id == player_id).first()
                
                if not coach_exists:
                    rejected_events.append({
                        "title": ev.get("summary", "Sin título"),
                        "date": start_dt.strftime("%d/%m/%Y"),
                        "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                        "reason": f"Coach ID {coach_id} no existe en la base de datos",
                        "suggestion": "Verificar que el coach esté registrado en la aplicación"
                    })
                    logger.warning(f"⚠️ Coach ID {coach_id} no existe en BD - ignorando evento")
                    continue

                # 🔧 VALIDACIÓN FLEXIBLE CON FEEDBACK AL USUARIO
                is_valid, error_msg, warnings = validate_session_for_import(start_dt, end_dt)

                if not player_exists:
                    rejected_events.append({
                        "title": ev.get("summary", "Sin título"),
                        "date": start_dt.strftime("%d/%m/%Y"),
                        "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                        "reason": f"Player ID {player_id} no existe en la base de datos",
                        "suggestion": "Verificar que el player esté registrado en la aplicación"
                    })
                    logger.warning(f"⚠️ Player ID {player_id} no existe en BD - ignorando evento")
                    continue
                
                if not is_valid:
                    # RECHAZADO - feedback al usuario
                    rejected_events.append({
                        "title": ev.get("summary", "Sin título"),
                        "date": start_dt.strftime("%d/%m/%Y"),
                        "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                        "reason": error_msg,
                        "suggestion": "Corregir horarios en Google Calendar y ejecutar sync manual"
                    })
                    logger.error(f"❌ EVENTO RECHAZADO - {ev.get('summary', 'Sin título')}: {error_msg}")
                    continue
                
                # IMPORTADO - verificar si tiene warnings
                if warnings:
                    warning_events.append({
                        "title": ev.get("summary", "Sin título"),
                        "date": start_dt.strftime("%d/%m/%Y"),
                        "time": f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}",
                        "warnings": warnings
                    })
                    logger.warning(f"⚠️ EVENTO CON WARNINGS - {ev.get('summary', 'Sin título')}: {'; '.join(warnings)}")
                else:
                    logger.info(f"✅ Mapeado y validado - Coach ID: {coach_id}, Player ID: {player_id}")
                
                new_session = Session(
                    coach_id=coach_id,
                    player_id=player_id,
                    start_time=start_dt,
                    end_time=end_dt,
                    status=status,
                    notes=ev.get("description"),
                    calendar_event_id=ev_id,
                    source="calendar",
                    version=1
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
        sessions_in_window = db.query(Session).filter(
            Session.calendar_event_id != None,
            Session.start_time >= win_start,
            Session.start_time <= win_end
        ).all()

        # Crear dict de sesiones EN LA VENTANA
        window_sessions = {s.calendar_event_id: s for s in sessions_in_window}

        # Candidatos: event_ids de BD que NO aparecieron en la búsqueda de Calendar
        elimination_candidates = [
            ev_id for ev_id in window_sessions.keys() 
            if ev_id not in seen_ev_ids
        ]

        logger.info(f"🔍 Sesiones en ventana: {len(window_sessions)}")
        logger.info(f"🔍 Candidatos para eliminación: {len(elimination_candidates)}")

        # Si no aparece en la búsqueda de la ventana = eliminado
        if elimination_candidates:
            for ev_id in elimination_candidates:
                ses = window_sessions[ev_id]
                
                # Si el evento no apareció en la búsqueda dentro de la ventana de tiempo,
                # y la sesión SÍ está en esa ventana, entonces fue eliminado
                logger.info(f"🗑️ ELIMINANDO sesión #{ses.id} - evento {(ev_id[:8] if ev_id else 'N/A')}... no encontrado en ventana")
                db.delete(ses)
                deleted += 1

        if deleted == 0:
            logger.info("✅ No hay eventos para eliminar")

        # Commit final
        db.commit()
        
        elapsed_time = time.time() - start_time
        events_per_second = len(events) / elapsed_time if elapsed_time > 0 else 0

        logger.info(f"✅ SYNC COMPLETADA en {elapsed_time:.2f}s ({events_per_second:.1f} eventos/seg)")
        logger.info(f"📊 Resultados: {imported} importadas, {updated} actualizadas, {deleted} eliminadas")

        # Log resumen de problemas
        if rejected_events:
            logger.warning(f"🚫 {len(rejected_events)} eventos rechazados por problemas críticos")
        if warning_events:
            logger.warning(f"⚠️ {len(warning_events)} eventos importados con advertencias")

        return imported, updated, deleted, rejected_events, warning_events
        
    except Exception as e:
        # 🔧 MEJORAR LOGGING DE ERRORES
        if "403" in str(e):
            logger.error("❌ ERROR 403: Sin permisos para Google Calendar - verificar API keys")
        elif "404" in str(e):
            logger.error("❌ ERROR 404: Calendario no encontrado - verificar CALENDAR_ID")
        elif "JSON" in str(e) or "Expecting property name" in str(e):
            logger.error("❌ ERROR AUTH: Credenciales inválidas - verificar google_service_account.json")
        else:
            logger.error(f"❌ ERROR sincronización: {e}")
        
        db.rollback()
        raise
    finally:
        db.close()

def sync_calendar_to_db():
    """Función original que solo devuelve estadísticas básicas (para auto-sync)."""
    imported, updated, deleted, rejected_events, warning_events = sync_calendar_to_db_with_feedback()
    
    # Solo loggar problemas pero no devolver las listas (para auto-sync simple)
    if rejected_events:
        logger.warning(f"🚫 Auto-sync rechazó {len(rejected_events)} eventos")
    if warning_events:
        logger.warning(f"⚠️ Auto-sync importó {len(warning_events)} eventos con advertencias")
    
    return imported, updated, deleted

def _status_from_color(color: str) -> SessionStatus:
    """
    Dado un colorId de Google Calendar, devuelve el estado correspondiente.
    • Reds → CANCELED
    • Greens → COMPLETED
    • El resto → SCHEDULED
    """
    cid = str(color)

    # 1) Todos los rojos → canceled
    red_ids = {"11", "6", "5"}  # ajusta aquí si usas varios tonos de rojo
    if cid in red_ids:
        return SessionStatus.CANCELED

    # 2) Todos los verdes → completed
    green_ids = {"2", "10", "12", "13"}  # tonos de verde en tu paleta
    if cid in green_ids:
        return SessionStatus.COMPLETED

    # 3) El resto → scheduled
    return SessionStatus.SCHEDULED

def update_past_sessions():
    db = get_db_session()
    now = dt.datetime.now(dt.timezone.utc)
    todo = db.query(Session).filter(
        Session.status == SessionStatus.SCHEDULED,
        Session.end_time <= now
    ).all()
    for s in todo:
        s.status = SessionStatus.COMPLETED
        if s.calendar_event_id:
            patch_color(s.calendar_event_id, s.status)
    if todo:
        db.commit()
    return len(todo)

def get_sessions(
    start: dt.datetime,
    end: dt.datetime,
    coach_id: int | None = None,
    player_id: int | None = None,
    statuses: list[SessionStatus] | None = None,
):
    # Devuelve las sesiones filtradas y ordenadas por fecha de inicio.

    db = get_db_session()
    q = db.query(Session).filter(Session.start_time >= start,
                                 Session.start_time <= end)
    if coach_id:
        q = q.filter(Session.coach_id == coach_id)
    if player_id:
        q = q.filter(Session.player_id == player_id)
    if statuses:
        q = q.filter(Session.status.in_(statuses))
    return q.order_by(Session.start_time.asc()).all()
