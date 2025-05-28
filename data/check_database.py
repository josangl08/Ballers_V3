#!/usr/bin/env python3
# data/check_database.py
"""
Script de diagnóstico para verificar el estado de la base de datos
"""

import os
import sys
from datetime import datetime

# Agregar la ruta raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_PATH
from controllers.db import get_db_session, get_database_info, initialize_database
from models import User, Coach, Player, Admin, Session, TestResult

def check_database_status():
    """Verifica el estado completo de la base de datos."""
    
    print("🔍 DIAGNÓSTICO DE BASE DE DATOS")
    print("=" * 50)
    
    # Usar la nueva función de información
    db_info = get_database_info()
    
    print(f"📍 Ruta de la base de datos: {db_info['database_path']}")
    print(f"📁 Archivo existe: {'✅ SÍ' if db_info['exists'] else '❌ NO'}")
    print(f"🔧 BD inicializada: {'✅ SÍ' if db_info['is_initialized'] else '❌ NO'}")
    print(f"⚡ Engine activo: {'✅ SÍ' if db_info['engine_active'] else '❌ NO'}")
    
    if not db_info['exists']:
        print("\n❌ La base de datos no existe. Ejecuta 'data/seed_database.py' para crearla.")
        return False
    
    # Verificar tamaño del archivo
    file_size = db_info['size_bytes']
    print(f"📏 Tamaño del archivo: {file_size:,} bytes")
    
    if file_size < 1000:  # Menos de 1KB probablemente esté vacía
        print("⚠️  ADVERTENCIA: El archivo es muy pequeño, probablemente esté vacío")
    
    # Conectar a la base de datos
    try:
        db_session = get_db_session()
        print("✅ Conexión a la base de datos exitosa")
        
        # Verificar cada tabla
        tables_info = {
            "users": User,
            "admins": Admin,
            "coaches": Coach,
            "players": Player,
            "sessions": Session,
            "test_results": TestResult
        }
        
        print("\n📊 CONTEO DE REGISTROS:")
        print("-" * 30)
        
        total_records = 0
        for table_name, model in tables_info.items():
            try:
                count = db_session.query(model).count()
                total_records += count
                status = "✅" if count > 0 else "⚠️ "
                print(f"{status} {table_name:15}: {count:4} registros")
            except Exception as e:
                print(f"❌ {table_name:15}: ERROR - {e}")
        
        print("-" * 30)
        print(f"📈 TOTAL DE REGISTROS: {total_records}")
        
        # Verificar integridad básica
        print("\n🔧 VERIFICACIÓN DE INTEGRIDAD:")
        print("-" * 35)
        
        # Verificar que hay usuarios
        user_count = db_session.query(User).count()
        if user_count == 0:
            print("❌ No hay usuarios en el sistema")
            return False
        else:
            print(f"✅ Usuarios encontrados: {user_count}")
        
        # Verificar perfiles
        admin_count = db_session.query(Admin).count()
        coach_count = db_session.query(Coach).count()
        player_count = db_session.query(Player).count()
        
        print(f"✅ Administradores: {admin_count}")
        print(f"✅ Entrenadores: {coach_count}")
        print(f"✅ Jugadores: {player_count}")
        
        # Verificar que los perfiles coinciden con usuarios
        profile_total = admin_count + coach_count + player_count
        if profile_total != user_count:
            print(f"⚠️  ADVERTENCIA: Desajuste entre usuarios ({user_count}) y perfiles ({profile_total})")
        
        # Verificar usuarios de ejemplo
        print("\n👥 USUARIOS DE EJEMPLO:")
        print("-" * 25)
        
        sample_users = db_session.query(User).limit(5).all()
        for user in sample_users:
            print(f"  • {user.username} ({user.name}) - {user.user_type.name}")
        
        db_session.close()
        
        if total_records > 50:  # Umbral razonable para considerar que tiene datos
            print("\n✅ ¡BASE DE DATOS EN BUEN ESTADO!")
            return True
        else:
            print("\n⚠️  BASE DE DATOS PARECE VACÍA O CON POCOS DATOS")
            print("💡 Considera ejecutar 'python data/seed_database.py' para poblarla")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR AL CONECTAR A LA BASE DE DATOS:")
        print(f"   {str(e)}")
        print("\n💡 POSIBLES SOLUCIONES:")
        print("   1. Eliminar el archivo de base de datos y recrearlo")
        print("   2. Ejecutar 'python data/seed_database.py'")
        print("   3. Verificar permisos de archivos")
        return False

def repair_database():
    """Intenta reparar la base de datos eliminándola y recreándola."""
    print("\n🔧 REPARANDO BASE DE DATOS...")
    
    if os.path.exists(DATABASE_PATH):
        # Crear backup
        backup_path = f"{DATABASE_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(DATABASE_PATH, backup_path)
            print(f"💾 Backup creado: {backup_path}")
        except Exception as e:
            print(f"⚠️  No se pudo crear backup: {e}")
        
        # Eliminar base de datos corrupta
        try:
            os.remove(DATABASE_PATH)
            print("🗑️  Base de datos anterior eliminada")
        except Exception as e:
            print(f"❌ No se pudo eliminar la base de datos: {e}")
            return False
    
    # Recrear base de datos
    print("🔨 Recreando base de datos...")
    try:
        success = initialize_database()
        if success:
            print("✅ Base de datos recreada exitosamente")
            return True
        else:
            print("❌ Error al recrear la base de datos")
            return False
    except Exception as e:
        print(f"❌ Error durante la recreación: {e}")
        return False

if __name__ == "__main__":
    print(f"🕒 Ejecutado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    is_healthy = check_database_status()
    
    if not is_healthy:
        print("\n" + "="*50)
        response = input("\n¿Deseas reparar la base de datos? (s/N): ").lower()
        if response == 's':
            if repair_database():
                print("✅ Base de datos reparada. Ahora ejecuta 'python data/seed_database.py' para poblarla.")
            else:
                print("❌ No se pudo reparar la base de datos.")
    
    print("\n🏁 Diagnóstico completado.")