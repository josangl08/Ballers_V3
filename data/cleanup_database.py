#!/usr/bin/env python3
"""
Script standalone para limpiar campos duplicados en la base de datos.
Ejecutar desde la raíz del proyecto: python cleanup_database.py
"""

import sqlite3
import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path para importar config
sys.path.append(str(Path(__file__).parent))

def cleanup_duplicate_columns():
    """
    Limpia campos duplicados en la tabla sessions.
    """
    # Importar config desde el directorio raíz
    try:
        from config import DATABASE_PATH
    except ImportError:
        # Fallback si no puede importar config
        DATABASE_PATH = "data/ballers_app.db"
    
    print("🧹 LIMPIANDO CAMPOS DUPLICADOS EN BD")
    print("=" * 50)
    
    # Verificar que la BD existe
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Error: No se encuentra la base de datos en {DATABASE_PATH}")
        return False
    
    # Crear backup automático
    backup_path = f"{DATABASE_PATH}.backup_{int(__import__('time').time())}"
    try:
        import shutil
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"📦 Backup creado: {backup_path}")
    except Exception as e:
        print(f"⚠️ No se pudo crear backup: {e}")
        response = input("¿Continuar sin backup? (y/N): ")
        if response.lower() != 'y':
            return False
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # 1. Verificar qué campos duplicados existen
        cursor.execute("PRAGMA table_info(sessions)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        
        print("📋 Columnas actuales en sessions:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
            
        # Identificar duplicados sospechosos
        has_duplicates = False
        if 'last_synced_at' in column_names and 'last_sync_at' in column_names:
            has_duplicates = True
            print(f"\n🚨 Campos duplicados detectados: last_synced_at y last_sync_at")
            
        if 'is_deleted' in column_names:
            has_duplicates = True
            print(f"🚨 Campo obsoleto detectado: is_deleted")
            
        if not has_duplicates:
            print("✅ No se encontraron campos duplicados o obsoletos")
            conn.close()
            return True
            
        # Confirmar antes de proceder
        print(f"\n⚠️ ADVERTENCIA: Esto modificará la estructura de la base de datos")
        response = input("¿Continuar con la limpieza? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operación cancelada")
            conn.close()
            return False
        
        # 2. Crear tabla temporal sin duplicados
        print("📝 Creando tabla temporal...")
        
        # Definir columnas finales (sin duplicados)
        final_columns = """
            id INTEGER NOT NULL PRIMARY KEY,
            coach_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            status VARCHAR(9) NOT NULL,
            notes VARCHAR,
            created_at DATETIME NOT NULL,
            calendar_event_id VARCHAR,
            updated_at DATETIME,
            last_sync_at DATETIME,
            sync_hash VARCHAR(32),
            source VARCHAR(10) DEFAULT 'app',
            version INTEGER DEFAULT 1,
            is_dirty BOOLEAN DEFAULT 0,
            FOREIGN KEY(coach_id) REFERENCES coaches (coach_id),
            FOREIGN KEY(player_id) REFERENCES players (player_id)
        """
        
        cursor.execute(f"CREATE TABLE sessions_clean ({final_columns})")
        
        # 3. Migrar datos (usar last_sync_at, descartar last_synced_at)
        print("📦 Migrando datos...")
        
        # Construir SQL dinámico basado en columnas existentes
        base_columns = "id, coach_id, player_id, start_time, end_time, status, notes, created_at, calendar_event_id, updated_at"
        
        # Manejar last_sync_at vs last_synced_at
        if 'last_sync_at' in column_names and 'last_synced_at' in column_names:
            sync_column = "COALESCE(last_sync_at, last_synced_at) as last_sync_at"
        elif 'last_sync_at' in column_names:
            sync_column = "last_sync_at"
        elif 'last_synced_at' in column_names:
            sync_column = "last_synced_at as last_sync_at"
        else:
            sync_column = "NULL as last_sync_at"
        
        # Manejar columnas opcionales
        optional_columns = []
        for col in ['sync_hash', 'source', 'version', 'is_dirty']:
            if col in column_names:
                optional_columns.append(col)
            else:
                if col == 'source':
                    optional_columns.append("'app' as source")
                elif col == 'version':
                    optional_columns.append("1 as version")
                elif col == 'is_dirty':
                    optional_columns.append("0 as is_dirty")
                else:
                    optional_columns.append(f"NULL as {col}")
        
        select_columns = f"{base_columns}, {sync_column}, {', '.join(optional_columns)}"
        
        migrate_sql = f"""
            INSERT INTO sessions_clean (
                id, coach_id, player_id, start_time, end_time, status, notes,
                created_at, calendar_event_id, updated_at, last_sync_at,
                sync_hash, source, version, is_dirty
            )
            SELECT {select_columns}
            FROM sessions
        """
        
        cursor.execute(migrate_sql)
        
        # 4. Verificar conteo antes de reemplazar
        cursor.execute("SELECT COUNT(*) FROM sessions")
        original_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sessions_clean")
        migrated_count = cursor.fetchone()[0]
        
        if original_count != migrated_count:
            print(f"❌ Error: Conteos no coinciden. Original: {original_count}, Migrado: {migrated_count}")
            conn.rollback()
            conn.close()
            return False
        
        # 5. Reemplazar tabla original
        print("🔄 Reemplazando tabla original...")
        cursor.execute("DROP TABLE sessions")
        cursor.execute("ALTER TABLE sessions_clean RENAME TO sessions")
        
        # 6. Verificar resultado final
        cursor.execute("PRAGMA table_info(sessions)")
        new_columns = cursor.fetchall()
        
        print("\n✅ Limpieza completada!")
        print("📋 Columnas finales:")
        for col in new_columns:
            print(f"   - {col[1]} ({col[2]})")
            
        # 7. Verificar integridad final
        cursor.execute("SELECT COUNT(*) FROM sessions")
        final_count = cursor.fetchone()[0]
        print(f"📊 Total sesiones preservadas: {final_count}")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎯 BD limpiada exitosamente!")
        print(f"📦 Backup guardado en: {backup_path}")
        print(f"🚀 Reinicia la aplicación para ver los cambios")
        return True
        
    except Exception as e:
        print(f"❌ Error limpiando BD: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🔧 Script de limpieza de base de datos")
    print("Este script eliminará campos duplicados en la tabla sessions")
    print()
    
    success = cleanup_duplicate_columns()
    
    if success:
        print("\n✅ Limpieza completada exitosamente")
        sys.exit(0)
    else:
        print("\n❌ Limpieza falló")
        sys.exit(1)