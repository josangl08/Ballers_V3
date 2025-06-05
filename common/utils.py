"""
Utilidades compartidas para toda la aplicación Ballers.
Funciones reutilizables que no dependen de UI específica.
"""
import hashlib
import datetime as dt
from typing import Optional


def hash_password(password: str) -> str:
    """
    Convierte una contraseña en un hash SHA-256.
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        str: Hash SHA-256 de la contraseña
    """
    return hashlib.sha256(password.encode()).hexdigest()


def format_time_local(dt_obj: Optional[dt.datetime]) -> str:
    """
    Convierte datetime UTC a hora local Madrid para logging legible.
    
    Args:
        dt_obj: Datetime object (puede ser None)
        
    Returns:
        str: Hora formateada en formato HH:MM o "None"
    """
    if dt_obj is None:
        return "None"
        
    # Asegurar que tiene timezone info
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
    
    # Convertir a hora de Madrid
    from zoneinfo import ZoneInfo
    try:
        local_tz = ZoneInfo("Europe/Madrid")
        local_time = dt_obj.astimezone(local_tz)
        return local_time.strftime('%H:%M')
    except:
        # Fallback si no funciona ZoneInfo
        return dt_obj.strftime('%H:%M')


def normalize_datetime_for_hash(dt_obj) -> str:
    """
    Normaliza datetime para hash: convierte a UTC y quita timezone info.
    
    Args:
        dt_obj: Datetime object o string ISO
        
    Returns:
        str: Datetime normalizado en formato ISO
    """
    if dt_obj is None:
        return ""
    
    # Si es string, convertir a datetime primero
    if isinstance(dt_obj, str):
        try:
            dt_obj = dt.datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
        except:
            return dt_obj  # Si falla, devolver como está
    
    # Manejar datetime naive (asumir timezone local Madrid)
    if dt_obj.tzinfo is None:
        try:
            from zoneinfo import ZoneInfo
            local_tz = ZoneInfo("Europe/Madrid")
            dt_obj = dt_obj.replace(tzinfo=local_tz)
        except:
            # Fallback: usar offset fijo +02:00
            dt_obj = dt_obj.replace(tzinfo=dt.timezone(dt.timedelta(hours=2)))
    
    # Convertir a UTC y quitar timezone info para consistencia
    utc_naive = dt_obj.astimezone(dt.timezone.utc).replace(tzinfo=None)
    
    # Devolver formato ISO sin microsegundos
    return utc_naive.replace(microsecond=0).isoformat()

