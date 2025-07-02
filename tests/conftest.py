# tests/conftest.py
"""
Configuración global para tests de pytest.
Fixtures compartidas entre todos los tests.
"""
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.utils import hash_password
from controllers.db import get_db_session
from models import Admin, Base, Coach, Player, User, UserType


@pytest.fixture(scope="function")
def test_db():
    """
    Crea una base de datos temporal en memoria para cada test.
    Se limpia automáticamente después de cada test.
    """
    # Crear BD en memoria (ultra rápida)
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    # Crear sesión
    Session = sessionmaker(bind=engine)
    session = Session()

    # Datos básicos para tests
    _create_test_users(session)

    yield session

    # Cleanup
    session.close()


@pytest.fixture(scope="function")
def test_admin_user():
    """Usuario admin para tests"""
    return {
        "username": "test_admin",
        "password": "admin123",
        "name": "Test Administrator",
        "user_type": UserType.admin,
    }


@pytest.fixture(scope="function")
def test_coach_user():
    """Usuario coach para tests"""
    return {
        "username": "test_coach",
        "password": "coach123",
        "name": "Test Coach",
        "user_type": UserType.coach,
    }


@pytest.fixture(scope="function")
def test_player_user():
    """Usuario player para tests"""
    return {
        "username": "test_player",
        "password": "player123",
        "name": "Test Player",
        "user_type": UserType.player,
    }


def _create_test_users(session):
    """Crea usuarios básicos para tests"""

    # Admin user
    admin_user = User(
        username="test_admin",
        password_hash=hash_password("admin123"),
        name="Test Administrator",
        email="admin@test.com",
        user_type=UserType.admin,
        is_active=True,
    )
    session.add(admin_user)
    session.flush()  # Para obtener el ID

    admin_user.permit_level = 5  # Configurar permit_level en el user
    admin = Admin(admin_id=admin_user.user_id, user=admin_user, role="Super Admin")
    session.add(admin)

    # Coach user
    coach_user = User(
        username="test_coach",
        password_hash=hash_password("coach123"),
        name="Test Coach",
        email="coach@test.com",
        user_type=UserType.coach,
        is_active=True,
    )
    session.add(coach_user)
    session.flush()

    coach = Coach(coach_id=coach_user.user_id, user=coach_user, license="UEFA B")
    session.add(coach)

    # Player user
    player_user = User(
        username="test_player",
        password_hash=hash_password("player123"),
        name="Test Player",
        email="player@test.com",
        user_type=UserType.player,
        is_active=True,
    )
    session.add(player_user)
    session.flush()

    player = Player(
        player_id=player_user.user_id,
        user=player_user,
        service="Premium",
        enrolment=1,
        notes="Test player notes",
    )
    session.add(player)

    # Commit all changes
    session.commit()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Configuración automática para todos los tests.
    Se ejecuta antes de cada test.
    """
    # Variables de entorno para tests
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("ENVIRONMENT", "testing")

    # Usar BD temporal
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()
    monkeypatch.setenv("DATABASE_PATH", temp_db.name)

    yield

    # Cleanup
    if os.path.exists(temp_db.name):
        os.unlink(temp_db.name)


# Funciones helper para tests
def assert_user_data(user, expected_username, expected_user_type):
    """Helper para verificar datos de usuario"""
    assert user is not None
    assert user.username == expected_username
    assert user.user_type == expected_user_type
    assert user.is_active == True


def assert_successful_auth(success, message, user):
    """Helper para verificar autenticación exitosa"""
    assert success == True
    assert user is not None
    assert "welcome" in message.lower() or "bienvenido" in message.lower()


def assert_failed_auth(success, message, user):
    """Helper para verificar autenticación fallida"""
    assert success == False
    assert user is None
    assert message is not None
    assert len(message) > 0
