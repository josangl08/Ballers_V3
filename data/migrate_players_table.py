#!/usr/bin/env python3
"""
Migración de Base de Datos: Añadir columnas is_professional y wyscout_id
Script para migrar la tabla players añadiendo las nuevas columnas preservando todos los datos.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import text

# Añadir el directorio raíz al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from controllers.db import get_db_session
from models import Player, User

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("data/migration.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class PlayerTableMigration:
    """
    Maneja la migración de la tabla players para añadir nuevas columnas.
    """

    def __init__(self):
        self.backup_table_name = (
            f"players_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.migration_successful = False

    def check_current_schema(self) -> Tuple[bool, List[str]]:
        """
        Verifica el esquema actual de la tabla players.

        Returns:
            Tuple[needs_migration, current_columns]
        """
        logger.info("🔍 Verificando esquema actual de la tabla players...")

        try:
            with get_db_session() as session:
                # Obtener información de columnas
                result = session.execute(text("PRAGMA table_info(players)")).fetchall()
                columns = [row[1] for row in result]

                logger.info(f"📋 Columnas actuales: {columns}")

                # Verificar si las nuevas columnas ya existen
                new_columns = ["is_professional", "wyscout_id"]
                missing_columns = [col for col in new_columns if col not in columns]

                if missing_columns:
                    logger.info(f"⚠️  Columnas faltantes: {missing_columns}")
                    return True, columns
                else:
                    logger.info("✅ Todas las columnas ya están presentes")
                    return False, columns

        except Exception as e:
            logger.error(f"❌ Error verificando esquema: {str(e)}")
            raise

    def count_existing_players(self) -> int:
        """
        Cuenta el número de jugadores existentes.

        Returns:
            Número de jugadores
        """
        try:
            with get_db_session() as session:
                # Usar query SQL directa para evitar errores de ORM
                result = session.execute(
                    text("SELECT COUNT(*) FROM players")
                ).fetchone()
                count = result[0] if result else 0
                logger.info(f"👥 Jugadores existentes: {count}")
                return count

        except Exception as e:
            logger.error(f"❌ Error contando jugadores: {str(e)}")
            raise

    def create_backup(self) -> bool:
        """
        Crea una copia de seguridad de la tabla players actual.

        Returns:
            True si el backup fue exitoso
        """
        logger.info(
            f"💾 Creando backup de tabla players como {self.backup_table_name}..."
        )

        try:
            with get_db_session() as session:
                # Crear tabla de backup
                backup_sql = f"""
                CREATE TABLE {self.backup_table_name} AS
                SELECT * FROM players
                """
                session.execute(text(backup_sql))
                session.commit()

                # Verificar que el backup se creó correctamente
                result = session.execute(
                    text(f"SELECT COUNT(*) FROM {self.backup_table_name}")
                ).fetchone()
                backup_count = result[0] if result else 0

                logger.info(f"✅ Backup creado exitosamente: {backup_count} registros")
                return True

        except Exception as e:
            logger.error(f"❌ Error creando backup: {str(e)}")
            return False

    def create_new_players_table(self) -> bool:
        """
        Crea la nueva tabla players con las columnas adicionales.

        Returns:
            True si la tabla se creó exitosamente
        """
        logger.info("🔧 Creando nueva tabla players con columnas adicionales...")

        try:
            with get_db_session() as session:
                # Crear nueva tabla con estructura completa
                create_table_sql = """
                CREATE TABLE players_new (
                    player_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    service TEXT,
                    enrolment INTEGER DEFAULT 0,
                    notes TEXT,
                    is_professional INTEGER DEFAULT 0,
                    wyscout_id TEXT UNIQUE,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
                """
                session.execute(text(create_table_sql))
                session.commit()

                logger.info("✅ Nueva tabla players_new creada exitosamente")
                return True

        except Exception as e:
            logger.error(f"❌ Error creando nueva tabla: {str(e)}")
            return False

    def migrate_data(self) -> bool:
        """
        Migra los datos de la tabla original a la nueva tabla.

        Returns:
            True si la migración fue exitosa
        """
        logger.info("📦 Migrando datos de la tabla original...")

        try:
            with get_db_session() as session:
                # Migrar datos con valores por defecto para nuevas columnas
                migrate_sql = """
                INSERT INTO players_new (
                    player_id, user_id, service, enrolment, notes,
                    is_professional, wyscout_id
                )
                SELECT
                    player_id, user_id, service, enrolment, notes,
                    0 as is_professional,  -- False por defecto
                    NULL as wyscout_id     -- NULL por defecto
                FROM players
                """
                session.execute(text(migrate_sql))
                session.commit()

                # Verificar que se migraron todos los datos
                original_count = session.execute(
                    text("SELECT COUNT(*) FROM players")
                ).fetchone()[0]
                new_count = session.execute(
                    text("SELECT COUNT(*) FROM players_new")
                ).fetchone()[0]

                if original_count == new_count:
                    logger.info(f"✅ Migración exitosa: {new_count} registros migrados")
                    return True
                else:
                    logger.error(
                        f"❌ Error en migración: {original_count} original vs {new_count} migrados"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ Error migrando datos: {str(e)}")
            return False

    def replace_tables(self) -> bool:
        """
        Reemplaza la tabla original con la nueva tabla.

        Returns:
            True si el reemplazo fue exitoso
        """
        logger.info("🔄 Reemplazando tabla original con la nueva tabla...")

        try:
            with get_db_session() as session:
                # Renombrar tabla original
                session.execute(
                    text(f"ALTER TABLE players RENAME TO {self.backup_table_name}_old")
                )

                # Renombrar nueva tabla
                session.execute(text("ALTER TABLE players_new RENAME TO players"))

                session.commit()

                logger.info("✅ Tablas reemplazadas exitosamente")
                return True

        except Exception as e:
            logger.error(f"❌ Error reemplazando tablas: {str(e)}")
            return False

    def verify_migration(self) -> bool:
        """
        Verifica que la migración fue exitosa.

        Returns:
            True si la verificación fue exitosa
        """
        logger.info("🔍 Verificando integridad de la migración...")

        try:
            with get_db_session() as session:
                # Verificar estructura de la nueva tabla
                result = session.execute(text("PRAGMA table_info(players)")).fetchall()
                columns = [row[1] for row in result]

                required_columns = [
                    "player_id",
                    "user_id",
                    "service",
                    "enrolment",
                    "notes",
                    "is_professional",
                    "wyscout_id",
                ]

                missing_columns = [
                    col for col in required_columns if col not in columns
                ]

                if missing_columns:
                    logger.error(
                        f"❌ Columnas faltantes después de migración: {missing_columns}"
                    )
                    return False

                # Verificar datos
                count_result = session.execute(
                    text("SELECT COUNT(*) FROM players")
                ).fetchone()
                total_players = count_result[0] if count_result else 0

                # Verificar valores por defecto
                professional_result = session.execute(
                    text("SELECT COUNT(*) FROM players WHERE is_professional = 1")
                ).fetchone()
                professional_count = (
                    professional_result[0] if professional_result else 0
                )

                wyscout_result = session.execute(
                    text("SELECT COUNT(*) FROM players WHERE wyscout_id IS NOT NULL")
                ).fetchone()
                wyscout_count = wyscout_result[0] if wyscout_result else 0

                logger.info(f"📊 Verificación completada:")
                logger.info(f"   👥 Total jugadores: {total_players}")
                logger.info(f"   🏆 Jugadores profesionales: {professional_count}")
                logger.info(f"   🆔 Con WyscoutID: {wyscout_count}")
                logger.info(f"   📋 Columnas: {columns}")

                return True

        except Exception as e:
            logger.error(f"❌ Error en verificación: {str(e)}")
            return False

    def cleanup_backup_tables(self) -> bool:
        """
        Limpia tablas de backup temporales manteniendo el backup principal.

        Returns:
            True si la limpieza fue exitosa
        """
        logger.info("🧹 Limpiando tablas temporales...")

        try:
            with get_db_session() as session:
                # Eliminar tabla temporal si existe
                backup_old_name = f"{self.backup_table_name}_old"

                # Verificar si existe antes de eliminar
                check_result = session.execute(
                    text(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{backup_old_name}'"
                    )
                ).fetchone()

                if check_result:
                    session.execute(text(f"DROP TABLE {backup_old_name}"))
                    session.commit()
                    logger.info(f"🗑️  Tabla temporal {backup_old_name} eliminada")

                logger.info(f"💾 Backup principal mantenido: {self.backup_table_name}")
                return True

        except Exception as e:
            logger.error(f"❌ Error en limpieza: {str(e)}")
            return False

    def run_migration(self) -> bool:
        """
        Ejecuta el proceso completo de migración.

        Returns:
            True si la migración fue exitosa
        """
        logger.info("🚀 Iniciando migración de tabla players...")

        try:
            # 1. Verificar si necesita migración
            needs_migration, current_columns = self.check_current_schema()
            if not needs_migration:
                logger.info(
                    "✅ La tabla ya tiene las columnas necesarias. No se requiere migración."
                )
                return True

            # 2. Contar jugadores existentes
            original_count = self.count_existing_players()
            if original_count == 0:
                logger.warning(
                    "⚠️  No hay jugadores existentes. Creando tabla con nueva estructura..."
                )
                # Solo crear la estructura sin migrar datos
                with get_db_session() as session:
                    session.execute(text("DROP TABLE IF EXISTS players"))
                    session.commit()
                from models import Base

                with get_db_session() as session:
                    Base.metadata.create_all(session.bind)
                logger.info("✅ Tabla creada con nueva estructura")
                return True

            # 3. Crear backup
            if not self.create_backup():
                logger.error("❌ No se pudo crear backup. Abortando migración.")
                return False

            # 4. Crear nueva tabla
            if not self.create_new_players_table():
                logger.error("❌ No se pudo crear nueva tabla. Abortando migración.")
                return False

            # 5. Migrar datos
            if not self.migrate_data():
                logger.error("❌ No se pudieron migrar datos. Abortando migración.")
                return False

            # 6. Reemplazar tablas
            if not self.replace_tables():
                logger.error(
                    "❌ No se pudieron reemplazar tablas. Abortando migración."
                )
                return False

            # 7. Verificar migración
            if not self.verify_migration():
                logger.error("❌ La verificación de migración falló.")
                return False

            # 8. Limpiar tablas temporales
            self.cleanup_backup_tables()

            self.migration_successful = True
            logger.info("🎉 ¡Migración completada exitosamente!")
            logger.info(f"💾 Backup disponible en tabla: {self.backup_table_name}")

            return True

        except Exception as e:
            logger.error(f"❌ Error crítico en migración: {str(e)}")
            return False


def main():
    """Función principal para ejecutar la migración."""
    print("🔧 Migración de Tabla Players - Sistema de Estadísticas Profesionales")
    print("=" * 70)

    migration = PlayerTableMigration()

    try:
        success = migration.run_migration()

        if success:
            print("\n✅ MIGRACIÓN EXITOSA")
            print("La aplicación ahora puede usar las nuevas columnas:")
            print("  - is_professional: Para marcar jugadores profesionales")
            print("  - wyscout_id: Para linking con datos de liga tailandesa")
            print("\n💡 Próximos pasos:")
            print("  1. Reiniciar la aplicación")
            print("  2. Probar que todos los perfiles funcionan")
            print("  3. Marcar jugadores como profesionales según sea necesario")
        else:
            print("\n❌ MIGRACIÓN FALLIDA")
            print("Revisa los logs para más detalles.")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Migración interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
