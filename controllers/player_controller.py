# controllers/player_controller.py
"""
Controlador para manejo de jugadores.
Separa la lógica de negocio de las páginas de UI.
"""
import datetime as dt
from typing import List, Optional, Tuple, Dict, Any
from models import User, Player, Session, SessionStatus, TestResult
from controllers.db import get_db_session


class PlayerController:
    """
    Controlador para operaciones con jugadores.
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
    

    # Obtencion de jugadores
 
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """
        Obtiene un jugador por su ID.
        
        Args:
            player_id: ID del jugador
            
        Returns:
            Objeto Player o None si no existe
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        return self.db.query(Player).filter(Player.player_id == player_id).first()
    
    def get_player_by_user_id(self, user_id: int) -> Optional[Player]:
        """
        Obtiene un jugador por su user_id (para el usuario actual).
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Objeto Player o None si no existe
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        return self.db.query(Player).join(User).filter(User.user_id == user_id).first()
    
    def get_current_player(self, player_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[Player]:
        """
        Obtiene el jugador actual basado en los parámetros disponibles.
        Lógica unificada para obtener el jugador correcto.
        
        Args:
            player_id: ID específico del jugador (prioritario)
            user_id: ID del usuario (para el usuario actual)
            
        Returns:
            Objeto Player o None
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        # Prioridad: player_id específico
        if player_id is not None:
            return self.get_player_by_id(player_id)
        
        # Fallback: buscar por user_id
        if user_id is not None:
            return self.get_player_by_user_id(user_id)
        
        return None
    
    def get_active_players(self) -> List[Player]:
        """
        Obtiene todos los jugadores activos.
        
        Returns:
            Lista de jugadores activos
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        return self.db.query(Player).join(User).filter(User.is_active == True).all()
    
    def search_players(self, search_term: str) -> List[Player]:
        """
        Busca jugadores por nombre.
        
        Args:
            search_term: Término de búsqueda
            
        Returns:
            Lista de jugadores que coinciden
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        if not search_term:
            return self.get_active_players()
        
        return self.db.query(Player).join(User).filter(
            User.is_active == True,
            User.name.ilike(f"%{search_term}%")
        ).all()
    

    # Estadisticas y datos calculados

    def get_player_stats(self, player: Player) -> Dict[str, Any]:
        """
        Calcula estadísticas completas de un jugador.
        
        Args:
            player: Objeto Player
            
        Returns:
            Diccionario con estadísticas calculadas
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        # Calcular estadísticas de sesiones
        completed = sum(s.status == SessionStatus.COMPLETED for s in player.sessions)
        scheduled = sum(s.status == SessionStatus.SCHEDULED for s in player.sessions)
        canceled = sum(s.status == SessionStatus.CANCELED for s in player.sessions)
        
        # Calcular edad si hay fecha de nacimiento
        age = None
        if player.user.date_of_birth:
            today = dt.date.today()
            birth_date = player.user.date_of_birth.date()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        # Obtener próxima sesión programada
        next_session = self.db.query(Session).filter(
            Session.player_id == player.player_id,
            Session.status == SessionStatus.SCHEDULED,
            Session.start_time > dt.datetime.now()
        ).order_by(Session.start_time).first()
        
        next_session_text = "To be confirmed"
        if next_session:
            next_session_text = next_session.start_time.strftime("%d/%m/%Y %H:%M")
        
        return {
            "completed": completed,
            "scheduled": scheduled,
            "canceled": canceled,
            "remaining": max(player.enrolment - completed, 0),
            "age": age,
            "next_session": next_session_text,
            "next_session_obj": next_session
        }
    
    def get_player_card_data(self, player: Player) -> Dict[str, Any]:
        """
        Prepara datos de un jugador para mostrar en tarjeta.
        Usado en listas de jugadores.
        
        Args:
            player: Objeto Player
            
        Returns:
            Diccionario con datos formateados para tarjeta
        """
        stats = self.get_player_stats(player)
        
        return {
            "player_id": player.player_id,
            "name": player.user.name,
            "profile_photo": player.user.profile_photo,
            "age": stats["age"],
            "service": player.service,
            "enrolment": player.enrolment,
            "remaining": stats["remaining"],
            "next_session": stats["next_session"],
            "email": player.user.email,
            "phone": player.user.phone,
            "line": player.user.line
        }
    

    # Resultados de tests

    def get_player_test_results(self, player: Player) -> List[TestResult]:
        """
        Obtiene resultados de tests de un jugador ordenados por fecha.
        
        Args:
            player: Objeto Player
            
        Returns:
            Lista de TestResult ordenada por fecha descendente
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        return self.db.query(TestResult).filter(
            TestResult.player_id == player.player_id
        ).order_by(TestResult.date.desc()).all()
    
    def format_test_data_for_chart(self, test_results: List[TestResult]) -> List[Dict[str, Any]]:
        """
        Formatea resultados de tests para gráficos.
        
        Args:
            test_results: Lista de TestResult
            
        Returns:
            Lista de diccionarios para gráficos
        """
        test_data = []
        
        for test in test_results:
            test_dict = {
                "Date": test.date,
                "Ball Control": test.ball_control,
                "Control & Passing": test.control_pass,
                "Receiving & Passing/Scanning": test.receive_scan,
                "Dribling & Ball Carriying": test.dribling_carriying,
                "Shoot & Finishing": test.shooting,
                "Crossbar": test.crossbar,
                "Sprint": test.sprint,
                "T-test": test.t_test,
                "Jumping": test.jumping
            }
            test_data.append(test_dict)
        
        return test_data
    
    def get_test_metrics_list(self) -> List[str]:
        """
        Obtiene lista de métricas disponibles para gráficos.
        
        Returns:
            Lista de nombres de métricas
        """
        return [
            "Ball Control",
            "Control & Passing", 
            "Receiving & Passing/Scanning",
            "Dribling & Ball Carriying",
            "Shoot & Finishing",
            "Crossbar",
            "Sprint",
            "T-test",
            "Jumping"
        ]
    

    # Operaciones CRUD

    def update_player_notes(self, player: Player, notes: str) -> Tuple[bool, str]:
        """
        Actualiza las notas de un jugador.
        
        Args:
            player: Objeto Player
            notes: Nuevas notas
            
        Returns:
            Tuple (success, message)
        """
        if not self.db:
            raise RuntimeError("Controller debe usarse como context manager")
        
        try:
            player.notes = notes
            self.db.commit()
            return True, "Notes saved correctly"
        except Exception as e:
            self.db.rollback()
            return False, f"Error saving notes: {str(e)}"


def get_player_profile_data(player_id: Optional[int] = None, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Función de conveniencia para obtener datos completos de perfil.
    
    Args:
        player_id: ID específico del jugador
        user_id: ID del usuario (para jugador actual)
        
    Returns:
        Diccionario con todos los datos del perfil o None
    """
    with PlayerController() as controller:
        player = controller.get_current_player(player_id, user_id)
        
        if not player:
            return None
        
        stats = controller.get_player_stats(player)
        test_results = controller.get_player_test_results(player)
        
        return {
            "player": player,
            "stats": stats,
            "test_results": test_results,
            "user": player.user
        }


def get_players_for_list(search_term: str = "") -> List[Dict[str, Any]]:
    """
    Función de conveniencia para obtener jugadores para listas.
    
    Args:
        search_term: Término de búsqueda opcional
        
    Returns:
        Lista de diccionarios con datos de tarjetas
    """
    with PlayerController() as controller:
        players = controller.search_players(search_term)
        return [controller.get_player_card_data(player) for player in players]


def update_player_notes_simple(player_id: int, notes: str) -> Tuple[bool, str]:
    """
    Función de conveniencia para actualizar notas.
    
    Args:
        player_id: ID del jugador
        notes: Nuevas notas
        
    Returns:
        Tuple (success, message)
    """
    with PlayerController() as controller:
        player = controller.get_player_by_id(player_id)
        if not player:
            return False, "Player not found"
        
        return controller.update_player_notes(player, notes)