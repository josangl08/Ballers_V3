#!/usr/bin/env python3
# data/clean_duplicates.py
"""
Script de limpieza urgente para eliminar sesiones duplicadas
"""

import os
import sys
import shutil
from datetime import datetime, timezone
from sqlalchemy import func

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_PATH
from controllers.db_postgres import get_db_session
from models import Session

def backup_database():
    """Crear backup antes de la limpieza."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DATABASE_PATH}.backup_before_cleanup_{timestamp}"
    
    try:
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"✅ Backup creado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Error creando backup: {e}")
        return False

def find_duplicate_groups():
    """Encontrar grupos de sesiones duplicadas."""
    db = get_db_session()
    
    # Buscar duplicados por coach_id, player_id y fecha
    duplicates_query = db.query(
        Session.coach_id,
        Session.player_id, 
        func.date(Session.start_time).label('session_date'),
        func.count(Session.id).label('count')
    ).group_by(
        Session.coach_id,
        Session.player_id,
        func.date(Session.start_time)
    ).having(func.count(Session.id) > 1)
    
    duplicate_groups = duplicates_query.all()
    
    print(f"🔍 Encontrados {len(duplicate_groups)} grupos de duplicados")
    
    db.close()
    return duplicate_groups

def clean_duplicates_smart():
    """Limpiar duplicados conservando la sesión más completa."""
    db = get_db_session()
    
    # Encontrar grupos de sesiones duplicadas
    duplicate_groups_query = db.query(
        Session.coach_id,
        Session.player_id,
        func.date(Session.start_time).label('session_date')
    ).group_by(
        Session.coach_id,
        Session.player_id,
        func.date(Session.start_time)
    ).having(func.count(Session.id) > 1)
    
    duplicate_groups = duplicate_groups_query.all()
    
    total_deleted = 0
    total_kept = 0
    
    print(f"🧹 Procesando {len(duplicate_groups)} grupos de duplicados...")
    
    for group in duplicate_groups:
        # Obtener todas las sesiones de este grupo
        sessions_in_group = db.query(Session).filter(
            Session.coach_id == group.coach_id,
            Session.player_id == group.player_id,
            func.date(Session.start_time) == group.session_date
        ).order_by(Session.created_at.desc()).all()  # Más recientes primero
        
        if len(sessions_in_group) <= 1:
            continue
            
        print(f"   📅 Coach {group.coach_id} + Player {group.player_id} en {group.session_date}: {len(sessions_in_group)} duplicados")
        
        # Criterios para elegir la "mejor" sesión:
        # 1. La que tenga calendar_event_id (preferible)
        # 2. La más reciente (created_at)
        # 3. La que tenga más información (notas)
        
        def session_score(session):
            score = 0
            if session.calendar_event_id:
                score += 100  # Prioridad máxima
            if session.notes:
                score += len(session.notes or "")  # Más notas = mejor
            score += session.created_at.timestamp()  # Más reciente = mejor
            return score
        
        # Ordenar por score descendente
        sessions_sorted = sorted(sessions_in_group, key=session_score, reverse=True)
        
        # Conservar la primera (mejor score)
        session_to_keep = sessions_sorted[0]
        sessions_to_delete = sessions_sorted[1:]
        
        print(f"     ✅ Conservando sesión #{session_to_keep.id} (score: {session_score(session_to_keep):.0f})")
        
        # Eliminar las duplicadas
        for session in sessions_to_delete:
            print(f"     🗑️ Eliminando sesión #{session.id} (score: {session_score(session):.0f})")
            db.delete(session)
            total_deleted += 1
        
        total_kept += 1
    
    print(f"\n📊 Resumen de limpieza:")
    print(f"   ✅ Sesiones conservadas: {total_kept}")
    print(f"   🗑️ Sesiones eliminadas: {total_deleted}")
    
    # Confirmar antes de hacer commit
    response = input(f"\n¿Confirmar eliminación de {total_deleted} sesiones duplicadas? (s/N): ").lower()
    if response == 's':
        db.commit()
        print("✅ Limpieza completada y confirmada")
    else:
        db.rollback()
        print("❌ Limpieza cancelada")
    
    db.close()
    return total_deleted, total_kept

def verify_cleanup():
    """Verificar que la limpieza fue exitosa."""
    db = get_db_session()
    
    # Contar duplicados restantes
    remaining_duplicates = db.query(
        Session.coach_id,
        Session.player_id, 
        func.date(Session.start_time).label('date'),
        func.count(Session.id).label('count')
    ).group_by(
        Session.coach_id,
        Session.player_id,
        func.date(Session.start_time)
    ).having(func.count(Session.id) > 1).count()
    
    total_sessions = db.query(Session).count()
    with_event_id = db.query(Session).filter(Session.calendar_event_id != None).count()
    
    print(f"\n📊 ESTADO POST-LIMPIEZA:")
    print(f"   📈 Total sesiones: {total_sessions}")
    print(f"   🔗 Con calendar_event_id: {with_event_id}")
    print(f"   ⚠️ Grupos duplicados restantes: {remaining_duplicates}")
    
    if remaining_duplicates == 0:
        print("   ✅ ¡No hay duplicados restantes!")
    else:
        print(f"   🔴 Aún hay {remaining_duplicates} grupos duplicados")
    
    db.close()

def main():
    """Función principal de limpieza."""
    print("🧹 LIMPIEZA DE DUPLICADOS - MODO EMERGENCIA")
    print("=" * 50)
    
    # 1. Crear backup
    print("💾 Creando backup de seguridad...")
    backup_path = backup_database()
    if not backup_path:
        print("❌ No se pudo crear backup. Abortando.")
        return
    
    # 2. Mostrar estado actual
    duplicate_groups = find_duplicate_groups()
    if not duplicate_groups:
        print("✅ No hay duplicados para limpiar")
        return
    
    # 3. Proceder con limpieza
    print(f"\n🚨 Se encontraron duplicados que requieren limpieza")
    response = input("¿Continuar con la limpieza automática? (s/N): ").lower()
    if response != 's':
        print("❌ Limpieza cancelada")
        return
    
    # 4. Ejecutar limpieza
    deleted, kept = clean_duplicates_smart()
    
    # 5. Verificar resultado
    verify_cleanup()
    
    print(f"\n🎉 LIMPIEZA COMPLETADA")
    print(f"💾 Backup disponible: {backup_path}")

if __name__ == "__main__":
    main()