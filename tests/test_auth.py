# tests/test_auth.py
"""
Tests para el sistema de autenticación.
Tests críticos que DEBEN pasar antes y después de la migración a Dash.
"""
import pytest
from controllers.auth_controller import AuthController
from common.utils import hash_password
from .conftest import assert_successful_auth, assert_failed_auth


class TestAuthController:
    """Tests para AuthController - funcionalidad crítica"""

    def test_admin_login_success(self, test_db, test_admin_user):
        """
        TEST CRÍTICO: Admin puede hacer login con credenciales correctas
        """
        # ARRANGE
        username = test_admin_user["username"] 
        password = test_admin_user["password"]
        
        # ACT
        with AuthController() as auth:
            # Usar la BD de test en lugar de la real
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
        
        # ASSERT
        assert_successful_auth(success, message, user)
        assert user.user_type.name == "admin"

    def test_coach_login_success(self, test_db, test_coach_user):
        """
        TEST CRÍTICO: Coach puede hacer login con credenciales correctas
        """
        # ARRANGE 
        username = test_coach_user["username"]
        password = test_coach_user["password"]
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
        
        # ASSERT
        assert_successful_auth(success, message, user)
        assert user.user_type.name == "coach"

    def test_player_login_success(self, test_db, test_player_user):
        """
        TEST CRÍTICO: Player puede hacer login con credenciales correctas
        """
        # ARRANGE
        username = test_player_user["username"]
        password = test_player_user["password"]
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
        
        # ASSERT  
        assert_successful_auth(success, message, user)
        assert user.user_type.name == "player"

    def test_invalid_username_login_fails(self, test_db):
        """
        TEST CRÍTICO: Usuario inexistente NO puede hacer login
        """
        # ARRANGE
        username = "usuario_inexistente"
        password = "cualquier_password"
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
        
        # ASSERT
        assert_failed_auth(success, message, user)

    def test_invalid_password_login_fails(self, test_db, test_admin_user):
        """
        TEST CRÍTICO: Password incorrecta NO permite login
        """
        # ARRANGE
        username = test_admin_user["username"]
        password = "password_incorrecta"
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
        
        # ASSERT
        assert_failed_auth(success, message, user)

    def test_empty_credentials_login_fails(self, test_db):
        """
        TEST CRÍTICO: Credenciales vacías NO permiten login
        """
        # ARRANGE & ACT & ASSERT
        test_cases = [
            ("", ""),
            ("", "password"),
            ("username", ""),
            (None, None),
        ]
        
        for username, password in test_cases:
            with AuthController() as auth:
                auth.db = test_db
                success, message, user = auth.authenticate_user(username, password)
            
            assert_failed_auth(success, message, user)

    def test_session_creation_includes_user_data(self, test_db, test_admin_user):
        """
        TEST CRÍTICO: La sesión creada contiene todos los datos necesarios
        """
        # ARRANGE - Primero hacer login
        username = test_admin_user["username"]
        password = test_admin_user["password"]
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
            
            if success:
                session_data = auth.create_session(user, remember_me=False)
        
        # ASSERT
        assert success == True
        assert "user_id" in session_data
        assert "username" in session_data  
        assert "name" in session_data
        assert "user_type" in session_data
        assert "permit_level" in session_data
        
        assert session_data["username"] == username
        assert session_data["user_type"] == "admin"

    def test_session_creation_with_remember_me(self, test_db, test_admin_user):
        """
        TEST IMPORTANTE: Remember me funciona correctamente
        """
        # ARRANGE
        username = test_admin_user["username"]
        password = test_admin_user["password"]
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            success, message, user = auth.authenticate_user(username, password)
            
            if success:
                session_data = auth.create_session(user, remember_me=True)
        
        # ASSERT
        assert success == True
        assert session_data is not None
        # Nota: En tests no podemos verificar st.query_params 
        # pero podemos verificar que no crashea

    def test_get_user_by_id_success(self, test_db):
        """
        TEST IMPORTANTE: Obtener usuario por ID funciona
        """
        # ARRANGE - Usar el admin creado en conftest
        expected_user_id = 1  # Primer usuario creado
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            user = auth.get_user_by_id(expected_user_id)
        
        # ASSERT
        assert user is not None
        assert user.user_id == expected_user_id
        assert user.username == "test_admin"

    def test_get_user_by_invalid_id_returns_none(self, test_db):
        """
        TEST IMPORTANTE: ID inexistente retorna None
        """
        # ARRANGE
        invalid_user_id = 99999
        
        # ACT
        with AuthController() as auth:
            auth.db = test_db
            user = auth.get_user_by_id(invalid_user_id)
        
        # ASSERT
        assert user is None


class TestPasswordHashing:
    """Tests para utilidades de seguridad"""

    def test_password_hashing_consistency(self):
        """
        TEST CRÍTICO: Hash de password es consistente
        """
        # ARRANGE
        password = "mi_password_secreto"
        
        # ACT
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # ASSERT
        assert hash1 == hash2  # Mismo input = mismo hash
        assert hash1 != password  # Hash != password original
        assert len(hash1) == 64  # SHA-256 = 64 caracteres hex

    def test_different_passwords_different_hashes(self):
        """
        TEST CRÍTICO: Passwords diferentes = hashes diferentes  
        """
        # ARRANGE
        password1 = "password123"
        password2 = "password456"
        
        # ACT
        hash1 = hash_password(password1)
        hash2 = hash_password(password2)
        
        # ASSERT
        assert hash1 != hash2


# Tests de integración (más lentos pero más completos)
class TestAuthIntegration:
    """Tests de integración del flujo completo de autenticación"""

    def test_full_auth_flow_admin(self, test_db, test_admin_user):
        """
        TEST DE INTEGRACIÓN: Flujo completo admin
        Login → Crear sesión → Verificar permisos
        """
        username = test_admin_user["username"]
        password = test_admin_user["password"]
        
        with AuthController() as auth:
            auth.db = test_db
            
            # 1. Login
            success, message, user = auth.authenticate_user(username, password)
            assert success == True
            
            # 2. Crear sesión
            session_data = auth.create_session(user)
            assert session_data["user_type"] == "admin"
            
            # 3. Verificar permisos admin
            assert auth.check_user_type(["admin"]) == True
            assert auth.check_user_type(["coach"]) == False
            assert auth.check_permission_level(5) == True

    def test_full_auth_flow_coach(self, test_db, test_coach_user):
        """
        TEST DE INTEGRACIÓN: Flujo completo coach
        """
        username = test_coach_user["username"]
        password = test_coach_user["password"]
        
        with AuthController() as auth:
            auth.db = test_db
            
            # 1. Login
            success, message, user = auth.authenticate_user(username, password)
            assert success == True
            
            # 2. Crear sesión  
            session_data = auth.create_session(user)
            assert session_data["user_type"] == "coach"
            
            # 3. Verificar permisos coach
            assert auth.check_user_type(["coach"]) == True
            assert auth.check_user_type(["admin"]) == False