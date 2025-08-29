# controllers/user_controller.py
"""
Controlador para manejo de usuarios.
Separa la lógica CRUD de usuarios de las páginas de UI.
"""
import datetime as dt
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import joinedload

from common.utils import hash_password
from controllers.db import get_db_session
from models import Admin, Coach, Player, ProfessionalStats, User, UserType


class UserController:
    """
    Controlador para operaciones CRUD con usuarios.
    Principio: Separar lógica de negocio de la presentación.
    """

    def __init__(self):
        self.db = None

    def __enter__(self):
        """Context manager para manejo automático de BD"""
        self.db = get_db_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión de BD automáticamente"""
        if self.db:
            self.db.close()

    # Validaciones basicas

    def _validate_user_data(
        self, name: str, username: str, email: str, password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validación básica de datos de usuario (independiente de Streamlit).

        """
        # Validar campos obligatorios
        if not name or not name.strip():
            return False, "The name is required."

        if not username or not username.strip():
            return False, "The username is required."

        if not email or not email.strip():
            return False, "The email is required."

        # Validar formato de email básico
        if "@" not in email or "." not in email.split("@")[-1]:
            return False, "The email format is invalid."

        # Validar username (solo alfanumérico y guiones bajos)
        if not username.replace("_", "").replace("-", "").isalnum():
            return (
                False,
                "The username can only contain letters, numbers, hyphens and underscores.",
            )

        # Validar longitud de username
        if len(username) < 3 or len(username) > 20:
            return False, "The username must be between 3 and 20 characters long."

        # Validar contraseña si se proporciona
        if password is not None:
            if len(password) < 6:
                return False, "The password must be at least 6 characters long."

        return True, ""

    def _save_profile_photo(self, uploaded_file, username: str) -> str:
        """
        Guarda la foto de perfil y devuelve la ruta.

        Args:
            uploaded_file: Archivo subido (desde Streamlit)
            username: Nombre de usuario para generar nombre único

        Returns:
            Ruta del archivo guardado
        """
        # Crear directorio si no existe
        photo_dir = "assets/profile_photos"
        if not os.path.exists(photo_dir):
            os.makedirs(photo_dir)

        # Generar nombre de archivo único
        file_ext = os.path.splitext(uploaded_file.name)[1]
        filename = f"{username}_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        file_path = os.path.join(photo_dir, filename)

        # Guardar archivo
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return file_path

    # Consultas y obtencion de datos

    def get_all_users(self) -> List[User]:
        """Obtiene todos los usuarios del sistema."""
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        return self.db.query(User).all()

    def get_users_by_type(self, user_type: UserType) -> List[User]:
        """
        Obtiene usuarios filtrados por tipo.

        Args:
            user_type: Tipo de usuario (UserType enum)

        Returns:
            Lista de usuarios del tipo especificado
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        return (
            self.db.query(User)
            .filter(User.user_type == user_type)
            .order_by(User.name)
            .all()
        )

    def get_coaches(self) -> List[Coach]:
        """
        Obtiene todos los coaches activos con sus datos de usuario.

        Returns:
            Lista de objetos Coach con relaciones User cargadas
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        return (
            self.db.query(Coach)
            .join(User)
            .options(joinedload(Coach.user))  # Eager loading para evitar lazy loading
            .filter(User.is_active.is_(True))
            .order_by(User.name)
            .all()
        )

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Obtiene un usuario por su ID.

        Args:
            user_id: ID del usuario

        Returns:
            Objeto User o None si no existe
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        return self.db.query(User).filter_by(user_id=user_id).first()

    def check_username_exists(
        self, username: str, exclude_user_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si un username ya existe.

        Args:
            username: Username a verificar
            exclude_user_id: ID de usuario a excluir de la búsqueda (para edición)

        Returns:
            True si el username ya existe
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        query = self.db.query(User).filter_by(username=username)

        if exclude_user_id:
            query = query.filter(User.user_id != exclude_user_id)

        return query.first() is not None

    def check_email_exists(
        self, email: str, exclude_user_id: Optional[int] = None
    ) -> bool:
        """
        Verifica si un email ya existe.

        Args:
            email: Email a verificar
            exclude_user_id: ID de usuario a excluir de la búsqueda (para edición)

        Returns:
            True si el email ya existe
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        query = self.db.query(User).filter_by(email=email)

        if exclude_user_id:
            query = query.filter(User.user_id != exclude_user_id)

        return query.first() is not None

    # Operaciones CRUD

    def create_user(
        self,
        name: str,
        username: str,
        email: str,
        password: str,
        user_type: str,
        phone: Optional[str] = None,
        line: Optional[str] = None,
        date_of_birth: Optional[dt.date] = None,
        profile_photo_file=None,  # Archivo de Streamlit
        **profile_data,  # Datos específicos del perfil (coach, player, admin)
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Crea un nuevo usuario con su perfil correspondiente.

        Args:
            name: Nombre completo
            username: Nombre de usuario
            email: Email
            password: Contraseña en texto plano
            user_type: Tipo de usuario ("coach", "player", "admin")
            phone: Teléfono opcional
            line: LINE ID opcional
            date_of_birth: Fecha de nacimiento opcional
            profile_photo_file: Archivo de foto de perfil (desde Streamlit)
            **profile_data: Datos específicos del perfil

        Returns:
            Tuple (success, message, user_object)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        # Validar datos básicos
        is_valid, error_msg = self._validate_user_data(name, username, email, password)
        if not is_valid:
            return False, error_msg, None

        # Verificar username y email únicos
        if self.check_username_exists(username):
            return False, "The username is already in use.", None

        if self.check_email_exists(email):
            return False, "The email is already in use.", None

        try:
            # Procesar foto de perfil
            profile_photo_path = "assets/profile_photos/default_profile.png"
            if profile_photo_file:
                profile_photo_path = self._save_profile_photo(
                    profile_photo_file, username
                )

            # Crear objeto usuario
            new_user = User(
                username=username,
                name=name,
                password_hash=hash_password(password),
                email=email,
                phone=phone,
                line=line,
                profile_photo=profile_photo_path,
                date_of_birth=(
                    dt.datetime.combine(date_of_birth, dt.datetime.min.time())
                    if date_of_birth
                    else None
                ),
                user_type=UserType[user_type],
                permit_level=profile_data.get("permit_level", 1),
            )

            self.db.add(new_user)
            self.db.flush()  # Para obtener el ID generado

            # Crear perfil específico según el tipo
            profile_created = self._create_user_profile(
                new_user, user_type, profile_data
            )
            if not profile_created:
                self.db.rollback()
                return False, f"Error creating {user_type} profile", None

            self.db.commit()
            return True, f"User {name} created successfully.", new_user

        except Exception as e:
            self.db.rollback()
            return False, f"Error creating user: {str(e)}", None

    def update_user(
        self,
        user_id: int,
        name: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        line: Optional[str] = None,
        date_of_birth: Optional[dt.date] = None,
        new_password: Optional[str] = None,
        is_active: Optional[bool] = None,
        new_user_type: Optional[str] = None,
        profile_photo_file=None,
        **profile_data,
    ) -> Tuple[bool, str]:
        """
        Actualiza un usuario existente
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"

        try:
            # Validar datos si se proporcionan
            if name or username or email:
                current_name = name or user.name
                current_username = username or user.username
                current_email = email or user.email
                is_valid, error_msg = self._validate_user_data(
                    current_name, current_username, current_email
                )
                if not is_valid:
                    return False, error_msg

            # Verificar username único si se está cambiando
            if username and username != user.username:
                if self.check_username_exists(username, exclude_user_id=user_id):
                    return False, "The username is already in use."

            # Verificar email único si se está cambiando
            if email and email != user.email:
                if self.check_email_exists(email, exclude_user_id=user_id):
                    return False, "The email is already in use."

            # Actualizar campos básicos
            if name is not None:
                user.name = name
            if username is not None:
                user.username = username
            if email is not None:
                user.email = email
            if phone is not None:
                user.phone = phone
            if line is not None:
                user.line = line
            if date_of_birth is not None:
                user.date_of_birth = dt.datetime.combine(
                    date_of_birth, dt.datetime.min.time()
                )
            if is_active is not None and hasattr(user, "is_active"):
                user.is_active = is_active

            # Actualizar foto de perfil
            if profile_photo_file is not None:
                try:
                    # Eliminar foto anterior si no es la predeterminada
                    if (
                        user.profile_photo
                        != "assets/profile_photos/default_profile.png"
                        and os.path.exists(user.profile_photo)
                    ):
                        try:
                            os.remove(user.profile_photo)
                        except OSError:
                            # Si no se puede eliminar, continuar
                            print(
                                f"Warning: Could not remove profile photo {user.profile_photo}"
                            )

                    # Guardar nueva foto
                    new_photo_path = self._save_profile_photo(
                        profile_photo_file, user.username
                    )
                    user.profile_photo = new_photo_path

                except Exception as e:
                    return False, f"Error updating profile photo: {str(e)}"

            # Actualizar contraseña si se proporciona
            if new_password:
                user.password_hash = hash_password(new_password)

            # Cambio de tipo de usuario si es necesario
            if new_user_type and new_user_type != user.user_type.name:
                success = self._change_user_type(user, new_user_type, profile_data)
                if not success:
                    self.db.rollback()
                    return False, f"Error changing user type to {new_user_type}"
            else:
                # Actualizar perfil del tipo actual
                self._update_user_profile(user, profile_data)

            self.db.commit()
            return True, f"User {user.name} updated successfully."

        except Exception as e:
            self.db.rollback()
            return False, f"Error updating user: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Elimina un usuario y su perfil asociado con snapshots selectivos.

        Maneja las sesiones asociadas:
        - Coach: Crea snapshots y reasigna sesiones futuras
        - Player: Crea snapshots y cancela sesiones futuras
        - Admin: Eliminación directa (no tiene sesiones)

        Args:
            user_id: ID del usuario a eliminar

        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"

        try:
            # PASO 1: Crear snapshots selectivos ANTES de eliminar
            snapshots_created = 0
            sessions_reassigned = 0
            sessions_canceled = 0

            if user.user_type == UserType.coach and user.coach_profile:
                snapshots_created = self._create_coach_snapshots(user)
                sessions_reassigned = self._handle_coach_future_sessions(
                    user.coach_profile.coach_id
                )

            elif user.user_type == UserType.player and user.player_profile:
                snapshots_created = self._create_player_snapshots(user)
                sessions_canceled = self._handle_player_future_sessions(
                    user.player_profile.player_id
                )

            # PASO 2: Eliminar perfil específico (lógica original)
            if user.user_type == UserType.coach and user.coach_profile:
                self.db.delete(user.coach_profile)
            elif user.user_type == UserType.player and user.player_profile:
                # IMPORTANTE: Eliminar ProfessionalStats primero para evitar errores
                professional_stats = (
                    self.db.query(ProfessionalStats)
                    .filter(
                        ProfessionalStats.player_id == user.player_profile.player_id
                    )
                    .all()
                )
                for stat in professional_stats:
                    self.db.delete(stat)
                self.db.delete(user.player_profile)
            elif user.user_type == UserType.admin and user.admin_profile:
                self.db.delete(user.admin_profile)

            # PASO 3: Eliminar foto de perfil si no es la predeterminada
            if (
                user.profile_photo != "assets/profile_photos/default_profile.png"
                and os.path.exists(user.profile_photo)
            ):
                try:
                    os.remove(user.profile_photo)
                except OSError:
                    print(
                        f"Warning: Could not remove old profile photo {user.profile_photo}"
                    )

            # PASO 4: Eliminar usuario
            user_name = user.name
            self.db.delete(user)
            self.db.commit()

            # PASO 5: Crear mensaje informativo
            message_parts = [f"User {user_name} successfully deleted"]

            if snapshots_created > 0:
                message_parts.append(f"{snapshots_created} session snapshots created")
            if sessions_reassigned > 0:
                message_parts.append(
                    f"{sessions_reassigned} future sessions reassigned"
                )
            if sessions_canceled > 0:
                message_parts.append(f"{sessions_canceled} future sessions canceled")

            return True, ". ".join(message_parts) + "."

        except Exception as e:
            self.db.rollback()
            return False, f"Error deleting user: {str(e)}"

    def toggle_user_status(self, user_id: int) -> Tuple[bool, str]:
        """
        Activa/desactiva un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")

        user = self.get_user_by_id(user_id)
        if not user:
            return False, "User not found"

        if not hasattr(user, "is_active"):
            return False, "User does not have active status field"

        try:
            user.is_active = not user.is_active
            status = "activated" if user.is_active else "deactivated"
            self.db.commit()

            return True, f"User {user.name} {status} successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Error changing user status: {str(e)}"

    # Metodos privados para perfiles

    def _create_user_profile(
        self, user: User, user_type: str, profile_data: Dict[str, Any]
    ) -> bool:
        """Crea el perfil específico según el tipo de usuario."""
        try:
            if user_type == "coach":
                coach_profile = Coach(
                    user_id=user.user_id, license=profile_data.get("license", "")
                )
                self.db.add(coach_profile)

            elif user_type == "player":
                # Procesar servicios
                services = profile_data.get("services", [])
                service_str = (
                    ", ".join(services) if isinstance(services, list) else str(services)
                )

                player_profile = Player(
                    user_id=user.user_id,
                    service=service_str,
                    enrolment=profile_data.get("enrolment", 0),
                    notes=profile_data.get("notes", ""),
                    is_professional=profile_data.get("is_professional", False),
                    wyscout_id=self._convert_wyscout_id_to_int(
                        profile_data.get("wyscout_id", None)
                    ),
                )
                self.db.add(player_profile)

            elif user_type == "admin":
                admin_profile = Admin(
                    user_id=user.user_id, role=profile_data.get("role", "")
                )
                self.db.add(admin_profile)

                # Actualizar nivel de permiso para admin
                if "permit_level" in profile_data:
                    user.permit_level = profile_data["permit_level"]

            return True

        except Exception as e:
            print(f"Error creating profile: {e}")
            return False

    def _update_user_profile(self, user: User, profile_data: Dict[str, Any]):
        """Actualiza el perfil específico del usuario."""
        try:
            if user.user_type == UserType.coach and user.coach_profile:
                if "license" in profile_data:
                    user.coach_profile.license = profile_data["license"]

            elif user.user_type == UserType.player and user.player_profile:
                if "services" in profile_data:
                    services = profile_data["services"]
                    service_str = (
                        ", ".join(services)
                        if isinstance(services, list)
                        else str(services)
                    )
                    user.player_profile.service = service_str

                if "enrolment" in profile_data:
                    user.player_profile.enrolment = profile_data["enrolment"]

                if "notes" in profile_data:
                    user.player_profile.notes = profile_data["notes"]

                # Campos profesionales - usar nueva lógica de producto
                if "is_professional" in profile_data:
                    new_is_professional = profile_data["is_professional"]
                    current_is_professional = user.player_profile.is_professional

                    # Si hay cambio en el estado profesional, usar estrategia especializada
                    if new_is_professional != current_is_professional:
                        # Commit cambios previos antes de manejar professional status
                        self.db.commit()

                        # Usar función especializada para el cambio de estado
                        success, message = handle_professional_status_change(
                            user.user_id, new_is_professional
                        )

                        if not success:
                            self.db.rollback()
                            return (
                                False,
                                f"Error updating professional status: {message}",
                            )
                    else:
                        # No hay cambio, solo actualizar el campo
                        user.player_profile.is_professional = new_is_professional

                if "wyscout_id" in profile_data:
                    user.player_profile.wyscout_id = self._convert_wyscout_id_to_int(
                        profile_data["wyscout_id"]
                    )

            elif user.user_type == UserType.admin and user.admin_profile:
                if "role" in profile_data:
                    user.admin_profile.role = profile_data["role"]

                if "permit_level" in profile_data:
                    user.permit_level = profile_data["permit_level"]

        except Exception as e:
            print(f"Error updating profile: {e}")

    def _change_user_type(
        self, user: User, new_user_type: str, profile_data: Dict[str, Any]
    ) -> bool:
        """Cambia el tipo de usuario eliminando el perfil anterior y creando uno nuevo."""
        try:
            # Eliminar perfil anterior
            if user.coach_profile:
                self.db.delete(user.coach_profile)
            if user.player_profile:
                self.db.delete(user.player_profile)
            if user.admin_profile:
                self.db.delete(user.admin_profile)

            # Cambiar tipo de usuario
            user.user_type = UserType[new_user_type]

            # Crear nuevo perfil
            return self._create_user_profile(user, new_user_type, profile_data)

        except Exception as e:
            print(f"Error changing user type: {e}")
            return False

    def _convert_wyscout_id_to_int(self, wyscout_id):
        """
        Convierte wyscout_id de string a int para consistencia con modelo de BD.

        Args:
            wyscout_id: Valor que puede ser string, int, o None

        Returns:
            int o None: wyscout_id como entero o None si no es válido
        """
        if wyscout_id is None or wyscout_id == "":
            return None

        try:
            # Si ya es entero, devolverlo tal como está
            if isinstance(wyscout_id, int):
                return wyscout_id

            # Si es string, convertir a entero
            if isinstance(wyscout_id, str):
                wyscout_id = wyscout_id.strip()
                if wyscout_id == "" or wyscout_id.lower() in ["none", "null", "n/a"]:
                    return None
                return int(wyscout_id)

        except (ValueError, TypeError):
            # Si la conversión falla, retornar None
            return None

        return None

    def _create_coach_snapshots(self, coach_user) -> int:
        """
        Crea snapshots selectivos para todas las sesiones de un coach.

        Args:
            coach_user: Usuario coach a eliminar

        Returns:
            Número de snapshots creados
        """
        from models.session_model import Session

        if not coach_user.coach_profile:
            return 0

        # Obtener todas las sesiones del coach
        sessions = (
            self.db.query(Session)
            .filter_by(coach_id=coach_user.coach_profile.coach_id)
            .all()
        )

        snapshots_created = 0
        coach_name_del = f"{coach_user.name} (DEL)"

        for session in sessions:
            # Solo crear snapshot si no existe ya
            if not session.coach_name_snapshot:
                session.coach_name_snapshot = coach_name_del
                session.coach_id = None  # Desreferenciar
                snapshots_created += 1

        return snapshots_created

    def _create_player_snapshots(self, player_user) -> int:
        """
        Crea snapshots selectivos para todas las sesiones de un player.

        Args:
            player_user: Usuario player a eliminar

        Returns:
            Número de snapshots creados
        """
        from models.session_model import Session

        if not player_user.player_profile:
            return 0

        # Obtener todas las sesiones del player
        sessions = (
            self.db.query(Session)
            .filter_by(player_id=player_user.player_profile.player_id)
            .all()
        )

        snapshots_created = 0
        player_name_del = f"{player_user.name} (DEL)"

        for session in sessions:
            # Solo crear snapshot si no existe ya
            if not session.player_name_snapshot:
                session.player_name_snapshot = player_name_del
                session.player_id = None  # Desreferenciar
                snapshots_created += 1

        return snapshots_created

    def _handle_coach_future_sessions(self, coach_id: int) -> int:
        """
        Maneja las sesiones futuras de un coach: las reasigna a otro coach activo.

        Args:
            coach_id: ID del coach a eliminar

        Returns:
            Número de sesiones reasignadas
        """
        from datetime import datetime, timezone

        from models.coach_model import Coach
        from models.session_model import Session, SessionStatus

        # Obtener sesiones futuras del coach
        future_sessions = (
            self.db.query(Session)
            .filter(
                Session.coach_id == coach_id,
                Session.start_time > datetime.now(timezone.utc),
                Session.status == SessionStatus.SCHEDULED,
            )
            .all()
        )

        if not future_sessions:
            return 0

        # Encontrar otro coach activo para reasignar
        from sqlalchemy.orm import joinedload
        available_coaches = (
            self.db.query(Coach)
            .options(joinedload(Coach.user))
            .join(User)
            .filter(User.is_active == True, Coach.coach_id != coach_id)
            .all()
        )

        if not available_coaches:
            # Si no hay coaches disponibles, cancelar las sesiones
            for session in future_sessions:
                session.status = SessionStatus.CANCELED
                session.notes = (
                    session.notes or ""
                ) + " [AUTO-CANCELED: No available coaches]"
            return len(future_sessions)

        # Reasignar a primer coach disponible (lógica simple)
        target_coach = available_coaches[0]
        sessions_reassigned = 0

        for session in future_sessions:
            session.coach_id = target_coach.coach_id
            # Actualizar snapshot con el nuevo coach
            session.coach_name_snapshot = target_coach.user.name if target_coach.user else f"Coach {target_coach.coach_id}"
            session.notes = (session.notes or "") + f" [REASSIGNED from deleted coach]"
            sessions_reassigned += 1

        return sessions_reassigned

    def _handle_player_future_sessions(self, player_id: int) -> int:
        """
        Maneja las sesiones futuras de un player: las cancela.

        Args:
            player_id: ID del player a eliminar

        Returns:
            Número de sesiones canceladas
        """
        from datetime import datetime, timezone

        from models.session_model import Session, SessionStatus

        # Obtener sesiones futuras del player
        future_sessions = (
            self.db.query(Session)
            .filter(
                Session.player_id == player_id,
                Session.start_time > datetime.now(timezone.utc),
                Session.status == SessionStatus.SCHEDULED,
            )
            .all()
        )

        sessions_canceled = 0

        for session in future_sessions:
            session.status = SessionStatus.CANCELED
            session.notes = (session.notes or "") + " [AUTO-CANCELED: Player deleted]"
            sessions_canceled += 1

        return sessions_canceled


def get_users_for_management(
    user_type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Función con nombres de claves ESTANDARIZADOS"""
    with UserController() as controller:

        if user_type_filter and user_type_filter != "All":
            users = (
                controller.db.query(User)
                .options(
                    joinedload(User.coach_profile),
                    joinedload(User.player_profile),
                    joinedload(User.admin_profile),
                )
                .filter(User.user_type == UserType[user_type_filter])
                .order_by(User.name)
                .all()
            )
        else:
            users = (
                controller.db.query(User)
                .options(
                    joinedload(User.coach_profile),
                    joinedload(User.player_profile),
                    joinedload(User.admin_profile),
                )
                .order_by(User.name)
                .all()
            )

        users_data = []
        for user in users:
            is_active = getattr(user, "is_active", True)

            # Cargar datos de relaciones ANTES de cerrar sesión
            profile_data = {}
            if user.user_type == UserType.coach and user.coach_profile:
                profile_data["coach_license"] = user.coach_profile.license
            elif user.user_type == UserType.player and user.player_profile:
                profile_data["player_service"] = user.player_profile.service
                profile_data["player_enrolment"] = user.player_profile.enrolment
                profile_data["player_notes"] = user.player_profile.notes
            elif user.user_type == UserType.admin and user.admin_profile:
                profile_data["admin_role"] = user.admin_profile.role

            users_data.append(
                {
                    "ID": user.user_id,
                    "Name": user.name,
                    "Username": user.username,
                    "Email": user.email,
                    "Phone": user.phone,
                    "Line": user.line,
                    "User Type": user.user_type.name,
                    "Active": "Yes" if is_active else "No",
                    "Active_Bool": is_active,
                    "profile_photo": user.profile_photo,  # 🔧 FIX: snake_case consistente
                    "date_of_birth": user.date_of_birth,  # 🔧 FIX: snake_case consistente
                    "permit_level": getattr(
                        user, "permit_level", 1
                    ),  # 🔧 FIX: snake_case consistente
                    "profile_data": profile_data,  # 🔧 FIX: snake_case consistente
                }
            )

        return users_data


# Función para obtener usuario individual con eager loading
def get_user_with_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene un usuario con todos sus datos de perfil cargados.
    Evita problemas de lazy loading.
    """
    with UserController() as controller:

        user = (
            controller.db.query(User)
            .options(
                joinedload(User.coach_profile),
                joinedload(User.player_profile),
                joinedload(User.admin_profile),
            )
            .filter(User.user_id == user_id)
            .first()
        )

        if not user:
            return None

        # Cargar todos los datos antes de cerrar sesión
        user_data = {
            "user_id": user.user_id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "line": user.line,
            "user_type": user.user_type.name,
            "is_active": getattr(user, "is_active", True),
            "profile_photo": user.profile_photo,
            "date_of_birth": user.date_of_birth,
            "permit_level": getattr(user, "permit_level", 1),
        }

        # Cargar datos específicos del perfil
        if user.user_type == UserType.coach and user.coach_profile:
            user_data["coach_license"] = user.coach_profile.license
        elif user.user_type == UserType.player and user.player_profile:
            user_data["player_service"] = user.player_profile.service
            user_data["player_enrolment"] = user.player_profile.enrolment
            user_data["player_notes"] = user.player_profile.notes
            # Campos profesionales
            user_data["is_professional"] = getattr(
                user.player_profile, "is_professional", False
            )
            user_data["wyscout_id"] = getattr(user.player_profile, "wyscout_id", None)
        elif user.user_type == UserType.admin and user.admin_profile:
            user_data["admin_role"] = user.admin_profile.role

        return user_data


def create_user_simple(user_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Función de conveniencia para crear usuario.
    Mantiene compatibilidad con código existente.
    """
    with UserController() as controller:
        success, message, _ = controller.create_user(**user_data)
        return success, message


def update_user_simple(user_id: int, **kwargs) -> Tuple[bool, str]:
    """
    Función de conveniencia para actualizar usuario.
    Mantiene compatibilidad con código existente.
    """
    with UserController() as controller:
        return controller.update_user(user_id, **kwargs)


def delete_user_simple(user_id: int) -> Tuple[bool, str]:
    """
    Función de conveniencia para eliminar usuario.
    Mantiene compatibilidad con código existente.
    """
    with UserController() as controller:
        return controller.delete_user(user_id)
