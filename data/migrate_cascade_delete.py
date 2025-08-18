#!/usr/bin/env python3
"""
Migración para añadir CASCADE DELETE a las relaciones player_id.

Este script actualiza las claves foráneas para que cuando se elimine un player,
también se eliminen automáticamente sus registros relacionados en ml_metrics
y professional_stats.
"""

import os
import sqlite3
from pathlib import Path

# Configuración
DB_PATH = Path(__file__).parent / "ballers_app.db"


def migrate_cascade_delete():
    """Migra la base de datos para añadir CASCADE DELETE."""

    if not DB_PATH.exists():
        print(f"❌ Base de datos no encontrada en {DB_PATH}")
        return False

    print(f"🔄 Iniciando migración CASCADE DELETE en {DB_PATH}")

    try:
        # Crear backup
        backup_path = DB_PATH.with_suffix(".db.backup_cascade")
        import shutil

        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Backup creado en {backup_path}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Habilitar claves foráneas
        cursor.execute("PRAGMA foreign_keys = ON")

        print("🔄 Actualizando tabla ml_metrics...")

        # Para SQLite, necesitamos recrear las tablas con CASCADE
        # 1. Crear nueva tabla ml_metrics con CASCADE (estructura exacta de la tabla real)
        cursor.execute(
            """
            CREATE TABLE ml_metrics_new (
                metric_id INTEGER PRIMARY KEY,
                player_id INTEGER NOT NULL,
                season VARCHAR NOT NULL,
                pdi_overall FLOAT,
                pdi_universal FLOAT,
                pdi_zone FLOAT,
                pdi_position_specific FLOAT,
                position_percentile FLOAT,
                league_percentile FLOAT,
                position_rank INTEGER,
                league_rank INTEGER,
                technical_proficiency FLOAT,
                tactical_intelligence FLOAT,
                physical_performance FLOAT,
                consistency_index FLOAT,
                model_version VARCHAR,
                position_analyzed VARCHAR,
                features_used INTEGER,
                last_calculated DATETIME,
                created_at DATETIME NOT NULL,
                updated_at DATETIME,
                FOREIGN KEY (player_id) REFERENCES players (player_id) ON DELETE CASCADE
            )
        """
        )

        # 2. Copiar datos existentes
        cursor.execute(
            """
            INSERT INTO ml_metrics_new
            SELECT * FROM ml_metrics
        """
        )

        # 3. Eliminar tabla antigua y renombrar
        cursor.execute("DROP TABLE ml_metrics")
        cursor.execute("ALTER TABLE ml_metrics_new RENAME TO ml_metrics")

        print("🔄 Actualizando tabla professional_stats...")

        # Hacer lo mismo para professional_stats
        cursor.execute(
            """
            CREATE TABLE professional_stats_new (
                stat_id INTEGER PRIMARY KEY,
                player_id INTEGER NOT NULL,
                wyscout_id INTEGER NOT NULL,
                season VARCHAR NOT NULL,
                player_name VARCHAR NOT NULL,
                full_name VARCHAR NOT NULL,
                team VARCHAR NOT NULL,
                team_within_timeframe VARCHAR,
                team_logo_url VARCHAR,
                competition VARCHAR DEFAULT 'Thai League',
                age INTEGER,
                birthday DATE,
                birth_country VARCHAR,
                passport_country VARCHAR,
                primary_position VARCHAR,
                secondary_position VARCHAR,
                third_position VARCHAR,
                matches_played INTEGER,
                minutes_played INTEGER,
                goals INTEGER,
                assists INTEGER,
                market_value INTEGER,
                height INTEGER,
                weight INTEGER,
                foot VARCHAR,
                shots INTEGER,
                shots_per_90 FLOAT,
                shots_on_target_pct FLOAT,
                goal_conversion_pct FLOAT,
                goals_per_90 FLOAT,
                assists_per_90 FLOAT,
                touches_in_box_per_90 FLOAT,
                shot_assists_per_90 FLOAT,
                defensive_actions_per_90 FLOAT,
                defensive_duels_per_90 FLOAT,
                defensive_duels_won_pct FLOAT,
                aerial_duels_per_90 FLOAT,
                aerial_duels_won_pct FLOAT,
                sliding_tackles_per_90 FLOAT,
                interceptions_per_90 FLOAT,
                fouls_per_90 FLOAT,
                passes_per_90 FLOAT,
                pass_accuracy_pct FLOAT,
                forward_passes_per_90 FLOAT,
                forward_passes_accuracy_pct FLOAT,
                back_passes_per_90 FLOAT,
                back_passes_accuracy_pct FLOAT,
                long_passes_per_90 FLOAT,
                long_passes_accuracy_pct FLOAT,
                progressive_passes_per_90 FLOAT,
                progressive_passes_accuracy_pct FLOAT,
                key_passes_per_90 FLOAT,
                duels_per_90 FLOAT,
                duels_won_pct FLOAT,
                offensive_duels_per_90 FLOAT,
                offensive_duels_won_pct FLOAT,
                dribbles_per_90 FLOAT,
                dribbles_success_pct FLOAT,
                progressive_runs_per_90 FLOAT,
                expected_goals FLOAT,
                expected_assists FLOAT,
                xg_per_90 FLOAT,
                xa_per_90 FLOAT,
                yellow_cards INTEGER,
                red_cards INTEGER,
                yellow_cards_per_90 FLOAT,
                red_cards_per_90 FLOAT,
                fouls_suffered_per_90 FLOAT,
                FOREIGN KEY (player_id) REFERENCES players (player_id) ON DELETE CASCADE
            )
        """
        )

        # Copiar datos de professional_stats con mapeo explícito
        cursor.execute(
            """
            INSERT INTO professional_stats_new (
                stat_id, player_id, wyscout_id, season, player_name, full_name,
                team, team_within_timeframe, team_logo_url, competition,
                age, birthday, birth_country, passport_country,
                primary_position, secondary_position, third_position,
                matches_played, minutes_played, goals, assists, market_value,
                height, weight, foot, shots, shots_per_90, shots_on_target_pct,
                goal_conversion_pct, goals_per_90, assists_per_90, touches_in_box_per_90,
                shot_assists_per_90, defensive_actions_per_90, defensive_duels_per_90,
                defensive_duels_won_pct, aerial_duels_per_90, aerial_duels_won_pct,
                sliding_tackles_per_90, interceptions_per_90, fouls_per_90,
                passes_per_90, pass_accuracy_pct, forward_passes_per_90,
                forward_passes_accuracy_pct, back_passes_per_90, back_passes_accuracy_pct,
                long_passes_per_90, long_passes_accuracy_pct, progressive_passes_per_90,
                progressive_passes_accuracy_pct, key_passes_per_90, duels_per_90,
                duels_won_pct, offensive_duels_per_90, offensive_duels_won_pct,
                dribbles_per_90, dribbles_success_pct, progressive_runs_per_90,
                expected_goals, expected_assists, xg_per_90, xa_per_90,
                yellow_cards, red_cards, yellow_cards_per_90, red_cards_per_90,
                fouls_suffered_per_90
            )
            SELECT
                stat_id, player_id, wyscout_id, season, player_name, full_name,
                team, team_within_timeframe, team_logo_url, competition,
                age, birthday, birth_country, passport_country,
                primary_position, secondary_position, third_position,
                matches_played, minutes_played, goals, assists, market_value,
                height, weight, foot, shots, shots_per_90, shots_on_target_pct,
                goal_conversion_pct, goals_per_90, assists_per_90, touches_in_box_per_90,
                shot_assists_per_90, defensive_actions_per_90, defensive_duels_per_90,
                defensive_duels_won_pct, aerial_duels_per_90, aerial_duels_won_pct,
                sliding_tackles_per_90, interceptions_per_90, fouls_per_90,
                passes_per_90, pass_accuracy_pct, forward_passes_per_90,
                forward_passes_accuracy_pct, back_passes_per_90, back_passes_accuracy_pct,
                long_passes_per_90, long_passes_accuracy_pct, progressive_passes_per_90,
                progressive_passes_accuracy_pct, key_passes_per_90, duels_per_90,
                duels_won_pct, offensive_duels_per_90, offensive_duels_won_pct,
                dribbles_per_90, dribbles_success_pct, progressive_runs_per_90,
                expected_goals, expected_assists, xg_per_90, xa_per_90,
                yellow_cards, red_cards, yellow_cards_per_90, red_cards_per_90,
                fouls_suffered_per_90
            FROM professional_stats
        """
        )

        # Eliminar tabla antigua y renombrar
        cursor.execute("DROP TABLE professional_stats")
        cursor.execute(
            "ALTER TABLE professional_stats_new RENAME TO professional_stats"
        )

        conn.commit()
        print("✅ Migración CASCADE DELETE completada exitosamente")

        # Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] == "ok":
            print("✅ Verificación de integridad: OK")
        else:
            print(f"⚠️ Verificación de integridad: {result[0]}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        # Restaurar backup si algo sale mal
        if backup_path.exists():
            shutil.copy2(backup_path, DB_PATH)
            print(f"🔄 Backup restaurado desde {backup_path}")
        return False


if __name__ == "__main__":
    print("🚀 Migración CASCADE DELETE para evitar errores de integridad referencial")
    print("=" * 60)

    success = migrate_cascade_delete()

    if success:
        print(
            "\n✅ Migración completada. Ahora los usuarios se pueden eliminar sin errores."
        )
    else:
        print("\n❌ Migración falló. Verificar logs de error.")
