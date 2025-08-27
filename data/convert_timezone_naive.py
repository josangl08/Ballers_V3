#!/usr/bin/env python3
"""
Script para convertir datos timezone-aware a timezone-naive en Supabase.
Convierte los campos datetime de la tabla sessions para ser compatibles
con el modelo timezone=False.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
# Cargar variables de entorno
load_dotenv()

from controllers.db import get_db_session, initialize_database
from sqlalchemy import text


def convert_timezone_to_naive():
    """Convierte datos timezone-aware a naive en la tabla sessions"""
    
    print("🔄 Iniciando conversión de timezone-aware a timezone-naive...")
    
    # Inicializar conexión
    if not initialize_database():
        print("❌ Error: No se pudo conectar a la base de datos")
        return False
    
    # Cerrar todas las conexiones existentes para liberar pool
    from controllers.db import close_all_connections
    close_all_connections()
    print("🔒 Pool de conexiones limpiado antes de conversión")
    
    # Crear scripts de conversión por separado
    check_script = """
        SELECT COUNT(*) as total_sessions
        FROM sessions;
    """
    
    conversion_script = """
        UPDATE sessions SET
            start_time = start_time AT TIME ZONE 'UTC',
            end_time = CASE 
                WHEN end_time IS NOT NULL 
                THEN end_time AT TIME ZONE 'UTC' 
                ELSE NULL 
            END,
            created_at = created_at AT TIME ZONE 'UTC',
            updated_at = updated_at AT TIME ZONE 'UTC',
            last_sync_at = CASE 
                WHEN last_sync_at IS NOT NULL 
                THEN last_sync_at AT TIME ZONE 'UTC' 
                ELSE NULL 
            END;
    """
    
    verify_script = """
        SELECT start_time, created_at, updated_at 
        FROM sessions 
        ORDER BY id 
        LIMIT 3;
    """
    
    try:
        with get_db_session() as db:
            print("📊 Ejecutando conversión de timezone...")
            
            # Verificar cantidad de sesiones antes
            check_result = db.execute(text(check_script))
            total_sessions = check_result.scalar()
            print(f"   Total sesiones encontradas: {total_sessions}")
            
            # Ejecutar el script de conversión
            result = db.execute(text(conversion_script))
            affected_rows = result.rowcount
            print(f"   Filas actualizadas: {affected_rows}")
            
            # Confirmar cambios
            db.commit()
            print("✅ Conversión completada exitosamente!")
            
            # Verificación adicional
            verify_result = db.execute(text(verify_script))
            
            print("\n🔍 Verificación - Primeras 3 sesiones:")
            for i, row in enumerate(verify_result, 1):
                print(f"   Sesión {i}:")
                print(f"     start_time: {row.start_time} (tipo: {type(row.start_time)})")
                print(f"     created_at: {row.created_at} (tipo: {type(row.created_at)})")
            
            return True
            
    except Exception as e:
        print(f"❌ Error durante la conversión: {e}")
        return False


def main():
    """Función principal"""
    print("🏗️ Iniciando conversión de datos timezone...")
    print("⚠️  ADVERTENCIA: Este script modifica datos en producción")
    print("✅ Ejecutando conversión automática...")
    
    # Ejecutar conversión
    success = convert_timezone_to_naive()
    
    if success:
        print("\n🎉 Conversión completada!")
        print("   - Todos los campos datetime ahora son timezone-naive")
        print("   - Compatible con modelo timezone=False")
        print("   - Listo para resolver el error de calendar display")
    else:
        print("\n💥 La conversión falló. Revisar logs de error.")


if __name__ == "__main__":
    main()