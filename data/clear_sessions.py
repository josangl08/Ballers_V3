#!/usr/bin/env python3
"""
Script para limpiar la base de datos de sesiones

Este script elimina todas las sesiones de entrenamiento de la base de datos
y opcionalmente también puede eliminar los eventos relacionados del Google Calendar.

Uso:
    python clear_sessions.py [--calendar] [--backup]

Opciones:
    --calendar: También elimina los eventos del Google Calendar
    --backup: Crea un backup antes de eliminar (recomendado)
"""

import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from config import DATABASE_PATH
from controllers.db import get_db_session
from models.session_model import Session


def create_backup():
    """Crea un backup de la base de datos antes de eliminar sesiones"""
    if os.path.exists(DATABASE_PATH):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{DATABASE_PATH}.backup_{timestamp}"
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"✅ Backup creado en: {backup_path}")
        return backup_path
    else:
        print("❌ Base de datos no encontrada")
        return None


def clear_sessions_from_db():
    """Elimina todas las sesiones de la base de datos"""
    db_session = get_db_session()

    try:
        # Contar sesiones antes de eliminar
        session_count = db_session.query(Session).count()
        print(f"📊 Sesiones encontradas: {session_count}")

        if session_count == 0:
            print("ℹ️ No hay sesiones para eliminar")
            return 0

        # Eliminar todas las sesiones
        deleted_count = db_session.query(Session).delete()
        db_session.commit()

        print(f"✅ {deleted_count} sesiones eliminadas de la base de datos")
        return deleted_count

    except Exception as e:
        print(f"❌ Error al eliminar sesiones: {e}")
        db_session.rollback()
        return 0
    finally:
        db_session.close()


def clear_sessions_from_calendar():
    """Elimina las sesiones del Google Calendar"""
    db_session = get_db_session()

    try:
        # Obtener todas las sesiones con calendar_event_id
        sessions_with_events = (
            db_session.query(Session)
            .filter(Session.calendar_event_id.isnot(None))
            .all()
        )

        if not sessions_with_events:
            print("ℹ️ No hay eventos de calendario para eliminar")
            return 0

        print(f"📊 Eventos de calendario encontrados: {len(sessions_with_events)}")
        print("⚠️ Funcionalidad de eliminación de calendario no implementada")
        print(
            "💡 Para eliminar eventos del calendario, use el script clear_calendar.py"
        )

        return 0

    except Exception as e:
        print(f"❌ Error al consultar eventos del calendario: {e}")
        return 0
    finally:
        db_session.close()


def verify_database_structure():
    """Verifica que la estructura de la base de datos esté intacta"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Verificar que las tablas existen
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('users', 'sessions', 'players', 'coaches', 'admins')
        """
        )
        tables = cursor.fetchall()

        print("\n📋 Estructura de la base de datos:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]}: {count} registros")

        conn.close()

    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")


def main():
    """Función principal"""
    print("🧹 Script de limpieza de sesiones - Ballers V3")
    print("=" * 50)

    # Verificar argumentos
    clear_calendar = "--calendar" in sys.argv
    create_backup_flag = "--backup" in sys.argv

    if clear_calendar:
        print("📅 Se eliminarán también los eventos del Google Calendar")

    if create_backup_flag:
        print("💾 Se creará un backup antes de eliminar")

    print("\n⚠️ ADVERTENCIA: Esta operación es irreversible")
    print("Se eliminarán TODAS las sesiones de la base de datos")

    if clear_calendar:
        print("También se eliminarán los eventos del Google Calendar")

    # Confirmación del usuario
    confirm = input(
        "\n¿Está seguro que desea continuar? (escriba 'CONFIRMAR' para continuar): "
    )

    if confirm != "CONFIRMAR":
        print("❌ Operación cancelada")
        return

    # Crear backup si se solicita
    if create_backup_flag:
        backup_path = create_backup()
        if not backup_path:
            print("❌ No se pudo crear backup. Cancelando operación.")
            return

    print("\n🚀 Iniciando limpieza...")

    # Eliminar eventos del calendario primero (si se solicita)
    if clear_calendar:
        print("\n1. Eliminando eventos del Google Calendar...")
        clear_sessions_from_calendar()

    # Eliminar sesiones de la base de datos
    print("\n2. Eliminando sesiones de la base de datos...")
    deleted_sessions = clear_sessions_from_db()

    # Verificar estructura final
    print("\n3. Verificando estructura de la base de datos...")
    verify_database_structure()

    print("\n✅ Limpieza completada")
    print(f"📊 Resumen:")
    print(f"  - Sesiones eliminadas: {deleted_sessions}")

    if clear_calendar:
        print(f"  - Eventos de calendario eliminados")

    if create_backup_flag:
        print(f"  - Backup creado: {backup_path}")

    print("\n💡 Puede usar 'python seed_calendar.py' para repoblar la base de datos")


if __name__ == "__main__":
    main()
