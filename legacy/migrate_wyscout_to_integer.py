#!/usr/bin/env python3
"""
Migración para convertir wyscout_id de String a Integer.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from controllers.db import get_db_session
from models import Player, ProfessionalStats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_wyscout_ids():
    """Convierte wyscout_ids de string a integer en la base de datos."""
    
    with get_db_session() as session:
        # 1. Migrar tabla players
        logger.info("Migrando wyscout_ids en tabla players...")
        
        players = session.query(Player).filter(
            Player.wyscout_id.isnot(None),
            Player.wyscout_id != ""
        ).all()
        
        for player in players:
            try:
                if isinstance(player.wyscout_id, str):
                    # Intentar convertir a entero
                    if player.wyscout_id.isdigit() or (player.wyscout_id.startswith('-') and player.wyscout_id[1:].isdigit()):
                        old_id = player.wyscout_id
                        player.wyscout_id = int(player.wyscout_id)
                        logger.info(f"Player {player.player_id}: '{old_id}' → {player.wyscout_id}")
                    else:
                        logger.warning(f"Player {player.player_id}: wyscout_id '{player.wyscout_id}' no es numérico, eliminando")
                        player.wyscout_id = None
            except ValueError as e:
                logger.error(f"Error convirtiendo wyscout_id '{player.wyscout_id}': {e}")
                player.wyscout_id = None
        
        # 2. Migrar tabla professional_stats
        logger.info("Migrando wyscout_ids en tabla professional_stats...")
        
        stats = session.query(ProfessionalStats).all()
        
        for stat in stats:
            try:
                if isinstance(stat.wyscout_id, str):
                    old_id = stat.wyscout_id
                    stat.wyscout_id = int(stat.wyscout_id)
                    logger.info(f"Stat {stat.stat_id}: '{old_id}' → {stat.wyscout_id}")
            except ValueError as e:
                logger.error(f"Error convirtiendo wyscout_id '{stat.wyscout_id}': {e}")
                # En professional_stats es obligatorio, eliminar registro
                logger.warning(f"Eliminando stat {stat.stat_id} por wyscout_id inválido")
                session.delete(stat)
        
        session.commit()
        logger.info("✅ Migración completada")


if __name__ == "__main__":
    try:
        migrate_wyscout_ids()
        print("✅ Migración de wyscout_id a Integer completada exitosamente")
    except Exception as e:
        print(f"❌ Error en migración: {str(e)}")
        import traceback
        traceback.print_exc()