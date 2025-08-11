"""
Fuzzy Matcher - Módulo de matching inteligente para jugadores profesionales.

Migrado desde ThaiLeagueController para consolidación ML.
Proporciona funciones de fuzzy matching para encontrar jugadores coincidentes
usando WyscoutID, nombres exactos y fuzzy matching.
"""

import logging
from typing import Dict, List

import pandas as pd
from fuzzywuzzy import fuzz

from controllers.db import get_db_session
from models.player_model import Player
from models.user_model import User, UserType

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """
    Matcher inteligente para encontrar jugadores coincidentes.
    Migrado desde ThaiLeagueController para usar en ml_system.
    """

    def __init__(self, session_factory=None):
        """Inicializa el matcher con session factory opcional."""
        self.session_factory = session_factory or get_db_session

    def find_matching_players(
        self, df: pd.DataFrame, threshold: int = 85
    ) -> Dict[str, List[Dict]]:
        """
        Encuentra jugadores coincidentes usando fuzzy matching.

        Migrado desde controllers.thai_league_controller para consolidación ML.

        Args:
            df: DataFrame con datos de jugadores
            threshold: Umbral de similitud (0-100)

        Returns:
            Diccionario con sugerencias de matching
        """
        logger.info(f"Iniciando matching de jugadores con threshold {threshold}")
        logger.info(f"📊 DataFrame recibido: {len(df)} registros")

        # Obtener jugadores profesionales existentes
        with self.session_factory() as session:
            existing_players = (
                session.query(Player, User)
                .join(User, Player.user_id == User.user_id)
                .filter(
                    Player.is_professional == True, User.user_type == UserType.player
                )
                .all()
            )

            logger.info(f"👥 Jugadores profesionales en BD: {len(existing_players)}")

        results = {
            "exact_matches": [],
            "fuzzy_matches": [],
            "no_matches": [],
            "multiple_matches": [],
        }

        for _, row in df.iterrows():
            full_name = row.get("Full name")
            wyscout_id = int(row.get("Wyscout id", 0))

            if not full_name:
                continue

            # Buscar matching exacto por WyscoutID
            exact_wyscout = self._find_by_wyscout_id(existing_players, wyscout_id)
            if exact_wyscout:
                results["exact_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "matched_player": exact_wyscout,
                        "confidence": 100,
                        "match_type": "wyscout_id",
                    }
                )
                continue

            # Buscar matching exacto por nombre
            exact_name = self._find_by_exact_name(existing_players, full_name)
            if exact_name:
                results["exact_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "matched_player": exact_name,
                        "confidence": 100,
                        "match_type": "exact_name",
                    }
                )
                continue

            # Buscar matching fuzzy
            fuzzy_matches = self._find_by_fuzzy_name(
                existing_players, full_name, threshold
            )

            if len(fuzzy_matches) == 1:
                results["fuzzy_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "matched_player": fuzzy_matches[0]["player"],
                        "confidence": fuzzy_matches[0]["confidence"],
                        "match_type": "fuzzy_name",
                    }
                )
            elif len(fuzzy_matches) > 1:
                results["multiple_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "candidates": fuzzy_matches,
                        "match_type": "multiple_fuzzy",
                    }
                )
            else:
                results["no_matches"].append(
                    {
                        "csv_player": full_name,
                        "wyscout_id": wyscout_id,
                        "match_type": "no_match",
                    }
                )

        # Log de resumen
        total_matches = len(results["exact_matches"]) + len(results["fuzzy_matches"])
        logger.info(f"✅ Matching completado:")
        logger.info(f"   • Exactos: {len(results['exact_matches'])}")
        logger.info(f"   • Fuzzy: {len(results['fuzzy_matches'])}")
        logger.info(f"   • Múltiples: {len(results['multiple_matches'])}")
        logger.info(f"   • Sin match: {len(results['no_matches'])}")
        logger.info(f"   • Total matches: {total_matches}/{len(df)}")

        return results

    def _find_by_wyscout_id(self, existing_players: List, wyscout_id: int) -> Dict:
        """Busca por WyscoutID exacto."""
        if not wyscout_id:
            return None

        for player, user in existing_players:
            if player.wyscout_id == wyscout_id:
                return {
                    "player_id": player.player_id,
                    "user_id": user.user_id,
                    "name": user.name,
                    "wyscout_id": player.wyscout_id,
                }
        return None

    def _find_by_exact_name(self, existing_players: List, full_name: str) -> Dict:
        """Busca por nombre exacto."""
        full_name_clean = full_name.strip().lower()

        for player, user in existing_players:
            if user.name.strip().lower() == full_name_clean:
                return {
                    "player_id": player.player_id,
                    "user_id": user.user_id,
                    "name": user.name,
                    "wyscout_id": player.wyscout_id,
                }
        return None

    def _find_by_fuzzy_name(
        self, existing_players: List, full_name: str, threshold: int
    ) -> List[Dict]:
        """Busca por fuzzy matching de nombres."""
        matches = []

        for player, user in existing_players:
            # Calcular similitudes usando diferentes algoritmos
            ratio = fuzz.ratio(full_name.lower(), user.name.lower())
            partial_ratio = fuzz.partial_ratio(full_name.lower(), user.name.lower())
            token_sort_ratio = fuzz.token_sort_ratio(
                full_name.lower(), user.name.lower()
            )

            # Usar la mejor puntuación
            confidence = max(ratio, partial_ratio, token_sort_ratio)

            if confidence >= threshold:
                matches.append(
                    {
                        "player": {
                            "player_id": player.player_id,
                            "user_id": user.user_id,
                            "name": user.name,
                            "wyscout_id": player.wyscout_id,
                        },
                        "confidence": confidence,
                        "similarity_scores": {
                            "ratio": ratio,
                            "partial_ratio": partial_ratio,
                            "token_sort_ratio": token_sort_ratio,
                        },
                    }
                )

        # Ordenar por confianza descendente
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches


# Función de conveniencia para compatibilidad
def find_matching_players(
    df: pd.DataFrame, threshold: int = 85
) -> Dict[str, List[Dict]]:
    """
    Función de conveniencia para fuzzy matching.
    Mantiene compatibilidad con código existente.

    Args:
        df: DataFrame con datos de jugadores
        threshold: Umbral de similitud (0-100)

    Returns:
        Diccionario con sugerencias de matching
    """
    matcher = FuzzyMatcher()
    return matcher.find_matching_players(df, threshold)
