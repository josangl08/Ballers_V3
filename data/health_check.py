# data/health_check.py
"""
Script de comprobación automática del sistema Ballers
Verifica que todo funcione correctamente después de los cambios
"""

import os
import sys
from datetime import datetime

# Agregar la ruta raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Verifica que todos los imports funcionen correctamente."""
    print("🔍 TESTING IMPORTS...")
    tests = [
        ("controllers.db", "get_db_session, initialize_database"),
        ("data.seed_database", "main"),
        ("models", "User, Coach, Player"),
        ("config", "DATABASE_PATH"),
    ]
    
    for module, items in tests:
        try:
            exec(f"from {module} import {items}")
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            return False
    return True

def test_database_connection():
    """Verifica la conexión a la base de datos."""
    print("\n🗄️  TESTING DATABASE CONNECTION...")
    try:
        from controllers.db import get_db_session, get_database_info
        
        # Info de la base de datos
        db_info = get_database_info()
        print(f"  📍 Database: {db_info['database_path']}")
        print(f"  📁 Exists: {'✅' if db_info['exists'] else '❌'}")
        print(f"  📏 Size: {db_info['size_bytes']:,} bytes")
        print(f"  🔧 Initialized: {'✅' if db_info['is_initialized'] else '❌'}")
        
        # Intentar conexión
        db_session = get_db_session()
        print("  ✅ Connection successful")
        
        db_session.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def test_data_integrity():
    """Verifica que los datos estén en la base de datos."""
    print("\n📊 TESTING DATA INTEGRITY...")
    try:
        from controllers.db import get_db_session
        from models import User, Coach, Player, Admin, Session, TestResult
        
        db_session = get_db_session()
        
        # Conteo de registros
        counts = {
            "Users": db_session.query(User).count(),
            "Coaches": db_session.query(Coach).count(),
            "Players": db_session.query(Player).count(),
            "Admins": db_session.query(Admin).count(),
            "Sessions": db_session.query(Session).count(),
            "Tests": db_session.query(TestResult).count(),
        }
        
        total_records = sum(counts.values())
        print(f"  📈 Total records: {total_records}")
        
        for table, count in counts.items():
            status = "✅" if count > 0 else "⚠️ " 
            print(f"  {status} {table}: {count}")
        
        # Verificar integridad básica
        if counts["Users"] == 0:
            print("  ❌ No users found - database is empty!")
            return False
        
        if counts["Users"] != (counts["Coaches"] + counts["Players"] + counts["Admins"]):
            print("  ⚠️  User count mismatch with profiles")
        
        db_session.close()
        
        if total_records > 50:
            print("  ✅ Database has sufficient data")
            return True
        else:
            print("  ⚠️  Database seems empty or underpopulated")
            return False
            
    except Exception as e:
        print(f"  ❌ Data integrity error: {e}")
        return False

def test_login_credentials():
    """Verifica que las credenciales de prueba funcionen."""
    print("\n🔐 TESTING LOGIN CREDENTIALS...")
    try:
        from common.login import login_user
        
        # Credenciales de prueba
        test_credentials = [
            ("admin1", "admin123"),
            ("coach1", "coach123"),
            ("player1", "player123"),
        ]
        
        for username, password in test_credentials:
            user = login_user(username, password)
            if user:
                print(f"  ✅ {username} ({user.user_type.name}): {user.name}")
            else:
                print(f"  ❌ {username}: Login failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Login test error: {e}")
        return False

def run_health_check():
    """Ejecuta todas las comprobaciones."""
    print("🏥 BALLERS HEALTH CHECK")
    print("=" * 50)
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("Data Integrity", test_data_integrity),
        ("Login Credentials", test_login_credentials),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name.upper()} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Resumen final
    print("\n" + "="*50)
    print("📋 HEALTH CHECK SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 RESULT: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ¡ALL TESTS PASSED! Your Ballers app is ready to go!")
        return True
    else:
        print("⚠️  Some tests failed. Check the details above.")
        print("💡 Try running:")
        print("   1. python data/check_database.py")
        print("   2. python data/seed_database.py")
        return False

if __name__ == "__main__":
    success = run_health_check()
    exit(0 if success else 1)