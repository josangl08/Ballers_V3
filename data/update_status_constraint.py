# data/update_status_constraint.py
# Script para actualizar el constraint de status en Supabase

import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers.db import get_db_session, initialize_database
from config import ENVIRONMENT

def update_status_constraint():
    """Actualizar constraint de sessions.status para aceptar valores lowercase"""
    
    print("🔧 Actualizando constraint sessions_status_check en Supabase...")
    
    initialize_database()
    
    with get_db_session() as db:
        try:
            # 1. Verificar constraint actual
            print("📋 Verificando constraint actual...")
            result = db.execute(text("""
                SELECT conname, pg_get_constraintdef(oid) as definition 
                FROM pg_constraint 
                WHERE conname = 'sessions_status_check'
            """))
            
            constraint_exists = False
            for row in result:
                constraint_exists = True
                print(f"  ✅ Constraint encontrado: {row.conname}")
                print(f"  📄 Definición actual: {row.definition}")
            
            if not constraint_exists:
                print("  ⚠️ Constraint no encontrado")
            
            # 2. Eliminar constraint existente si existe
            if constraint_exists:
                print("🗑️ Eliminando constraint existente...")
                db.execute(text("ALTER TABLE sessions DROP CONSTRAINT sessions_status_check"))
                print("  ✅ Constraint eliminado")
            
            # 3. Crear nuevo constraint con valores lowercase
            print("➕ Creando nuevo constraint con valores lowercase...")
            db.execute(text("""
                ALTER TABLE sessions 
                ADD CONSTRAINT sessions_status_check 
                CHECK (status IN ('completed', 'scheduled', 'canceled'))
            """))
            print("  ✅ Nuevo constraint creado")
            
            # 4. Commit cambios
            db.commit()
            print("💾 Cambios guardados")
            
            # 5. Verificar constraint actualizado
            print("🔍 Verificando constraint actualizado...")
            result = db.execute(text("""
                SELECT conname, pg_get_constraintdef(oid) as definition 
                FROM pg_constraint 
                WHERE conname = 'sessions_status_check'
            """))
            
            for row in result:
                print(f"  ✅ Constraint actualizado: {row.conname}")
                print(f"  📄 Nueva definición: {row.definition}")
            
            print("🎯 ¡Constraint actualizado correctamente!")
            
        except Exception as e:
            print(f"❌ Error actualizando constraint: {e}")
            db.rollback()
            raise

if __name__ == "__main__":
    print(f"🏗️ Actualizando constraint de status para entorno: {ENVIRONMENT}")
    update_status_constraint()