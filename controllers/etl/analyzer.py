"""
Analyzer Module - Análisis de datos y generación de estadísticas
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class StatsAnalyzer:
    """
    Analizador de estadísticas para datos de la liga tailandesa.
    Genera métricas de calidad, resúmenes y insights de los datos.
    """

    def __init__(self):
        """Inicializa el analizador."""
        pass

    def analyze_dataframe(
        self, df: pd.DataFrame, season: str
    ) -> Dict[str, any]:
        """
        Analiza un DataFrame completo y genera estadísticas comprensivas.
        
        Args:
            df: DataFrame a analizar
            season: Temporada siendo analizada
            
        Returns:
            Diccionario con estadísticas y análisis
        """
        logger.info(f"📊 Iniciando análisis de datos para {season}")
        
        analysis = {
            "season": season,
            "basic_stats": self._analyze_basic_stats(df),
            "data_quality": self._analyze_data_quality(df),
            "player_stats": self._analyze_player_stats(df),
            "team_stats": self._analyze_team_stats(df),
            "performance_insights": self._analyze_performance_insights(df),
            "summary": {}
        }
        
        # Generar resumen ejecutivo
        analysis["summary"] = self._generate_summary(analysis)
        
        logger.info(f"✅ Análisis completado para {season}")
        
        return analysis

    def _analyze_basic_stats(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza estadísticas básicas del DataFrame.
        
        Args:
            df: DataFrame a analizar
            
        Returns:
            Diccionario con estadísticas básicas
        """
        return {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "non_null_records": df.count().to_dict(),
            "null_percentages": ((df.isnull().sum() / len(df)) * 100).round(2).to_dict()
        }

    def _analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza calidad de los datos.
        
        Args:
            df: DataFrame a analizar
            
        Returns:
            Diccionario con métricas de calidad
        """
        quality_metrics = {
            "completeness": {},
            "consistency": {},
            "validity": {}
        }
        
        # Completeness - Qué tan completos están los datos
        critical_fields = ["Full name", "Wyscout id", "Competition"]
        for field in critical_fields:
            if field in df.columns:
                completeness = (df[field].notna().sum() / len(df)) * 100
                quality_metrics["completeness"][field] = round(completeness, 2)
        
        # Consistency - Consistencia en formatos
        if "Team" in df.columns:
            unique_teams = df["Team"].nunique()
            quality_metrics["consistency"]["unique_teams"] = unique_teams
            
        if "Competition" in df.columns:
            unique_competitions = df["Competition"].nunique() 
            quality_metrics["consistency"]["unique_competitions"] = unique_competitions
        
        # Validity - Validez de los datos
        if "Age" in df.columns:
            valid_ages = df[(df["Age"] >= 16) & (df["Age"] <= 50)]["Age"].count()
            total_ages = df["Age"].notna().sum()
            if total_ages > 0:
                quality_metrics["validity"]["age_validity_pct"] = round((valid_ages / total_ages) * 100, 2)
        
        return quality_metrics

    def _analyze_player_stats(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza estadísticas de jugadores.
        
        Args:
            df: DataFrame a analizar
            
        Returns:
            Diccionario con estadísticas de jugadores
        """
        player_stats = {}
        
        # Conteos básicos
        if "Full name" in df.columns:
            player_stats["total_players"] = df["Full name"].nunique()
            
        if "Age" in df.columns:
            ages = df["Age"].dropna()
            if len(ages) > 0:
                player_stats["age_distribution"] = {
                    "mean": round(ages.mean(), 1),
                    "median": round(ages.median(), 1),
                    "min": int(ages.min()),
                    "max": int(ages.max()),
                    "std": round(ages.std(), 1)
                }
        
        # Distribución por posiciones
        if "Primary position" in df.columns:
            position_counts = df["Primary position"].value_counts().to_dict()
            player_stats["position_distribution"] = position_counts
        
        # Estadísticas de rendimiento
        performance_fields = ["Goals", "Assists", "Minutes played", "Matches played"]
        performance_stats = {}
        
        for field in performance_fields:
            if field in df.columns:
                values = df[field].dropna()
                if len(values) > 0:
                    performance_stats[field.lower().replace(" ", "_")] = {
                        "mean": round(values.mean(), 2),
                        "median": round(values.median(), 2),
                        "max": round(values.max(), 2),
                        "total": round(values.sum(), 2)
                    }
        
        player_stats["performance"] = performance_stats
        
        return player_stats

    def _analyze_team_stats(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza estadísticas por equipos.
        
        Args:
            df: DataFrame a analizar
            
        Returns:
            Diccionario con estadísticas de equipos
        """
        team_stats = {}
        
        if "Team" in df.columns:
            # Excluir jugadores sin equipo para el análisis
            team_df = df[df["Team"].notna()]
            
            if len(team_df) > 0:
                team_stats["total_teams"] = team_df["Team"].nunique()
                
                # Jugadores por equipo
                players_per_team = team_df.groupby("Team").size()
                team_stats["players_per_team"] = {
                    "mean": round(players_per_team.mean(), 1),
                    "median": round(players_per_team.median(), 1),
                    "min": int(players_per_team.min()),
                    "max": int(players_per_team.max())
                }
                
                # Top equipos por número de jugadores
                team_stats["top_teams_by_players"] = players_per_team.sort_values(ascending=False).head(5).to_dict()
        
        # Jugadores sin equipo
        if "Team" in df.columns:
            players_without_team = df["Team"].isna().sum()
            team_stats["players_without_team"] = players_without_team
            team_stats["players_without_team_pct"] = round((players_without_team / len(df)) * 100, 2)
        
        return team_stats

    def _analyze_performance_insights(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Genera insights de rendimiento.
        
        Args:
            df: DataFrame a analizar
            
        Returns:
            Diccionario con insights de rendimiento
        """
        insights = {}
        
        # Top performers
        if "Goals" in df.columns:
            top_scorers = df.nlargest(5, "Goals")[["Full name", "Team", "Goals"]].to_dict("records")
            insights["top_scorers"] = top_scorers
        
        if "Assists" in df.columns:
            top_assisters = df.nlargest(5, "Assists")[["Full name", "Team", "Assists"]].to_dict("records")
            insights["top_assisters"] = top_assisters
        
        if "Minutes played" in df.columns:
            most_minutes = df.nlargest(5, "Minutes played")[["Full name", "Team", "Minutes played"]].to_dict("records")
            insights["most_minutes"] = most_minutes
        
        # Eficiencia
        if "Goals" in df.columns and "Shots" in df.columns:
            # Jugadores con mejor eficiencia de gol (min 5 disparos)
            efficiency_df = df[(df["Shots"] >= 5) & (df["Goals"].notna()) & (df["Shots"].notna())].copy()
            if len(efficiency_df) > 0:
                efficiency_df["goal_efficiency"] = efficiency_df["Goals"] / efficiency_df["Shots"]
                top_efficiency = efficiency_df.nlargest(5, "goal_efficiency")[
                    ["Full name", "Team", "Goals", "Shots", "goal_efficiency"]
                ].to_dict("records")
                insights["most_efficient_scorers"] = top_efficiency
        
        return insights

    def _generate_summary(self, analysis: Dict[str, any]) -> Dict[str, any]:
        """
        Genera resumen ejecutivo del análisis.
        
        Args:
            analysis: Análisis completo
            
        Returns:
            Diccionario con resumen ejecutivo
        """
        summary = {
            "season": analysis["season"],
            "data_overview": {},
            "quality_assessment": {},
            "key_insights": []
        }
        
        # Overview de datos
        basic = analysis["basic_stats"]
        summary["data_overview"] = {
            "total_records": basic["total_records"],
            "total_players": analysis["player_stats"].get("total_players", "N/A"),
            "total_teams": analysis["team_stats"].get("total_teams", "N/A"),
            "memory_usage_mb": basic["memory_usage_mb"]
        }
        
        # Evaluación de calidad
        quality = analysis["data_quality"]["completeness"]
        avg_completeness = sum(quality.values()) / len(quality) if quality else 0
        
        summary["quality_assessment"] = {
            "overall_completeness_pct": round(avg_completeness, 1),
            "players_without_team": analysis["team_stats"].get("players_without_team", 0),
            "data_quality_score": self._calculate_quality_score(analysis)
        }
        
        # Key insights
        insights = []
        
        if "top_scorers" in analysis["performance_insights"]:
            top_scorer = analysis["performance_insights"]["top_scorers"][0]
            insights.append(f"Máximo goleador: {top_scorer['Full name']} con {top_scorer['Goals']} goles")
        
        if analysis["team_stats"].get("players_without_team", 0) > 0:
            no_team_count = analysis["team_stats"]["players_without_team"]
            insights.append(f"Jugadores sin equipo: {no_team_count} (requiere revisión)")
        
        if "age_distribution" in analysis["player_stats"]:
            avg_age = analysis["player_stats"]["age_distribution"]["mean"]
            insights.append(f"Edad promedio: {avg_age} años")
        
        summary["key_insights"] = insights
        
        return summary

    def _calculate_quality_score(self, analysis: Dict[str, any]) -> float:
        """
        Calcula un score de calidad general (0-100).
        
        Args:
            analysis: Análisis completo
            
        Returns:
            Score de calidad (0-100)
        """
        score_components = []
        
        # Completeness score
        completeness = analysis["data_quality"]["completeness"]
        if completeness:
            avg_completeness = sum(completeness.values()) / len(completeness)
            score_components.append(avg_completeness * 0.4)  # 40% del score
        
        # Validity score
        validity = analysis["data_quality"]["validity"]
        if "age_validity_pct" in validity:
            score_components.append(validity["age_validity_pct"] * 0.3)  # 30% del score
        
        # Team assignment score (penalizar muchos jugadores sin equipo)
        if "players_without_team_pct" in analysis["team_stats"]:
            no_team_pct = analysis["team_stats"]["players_without_team_pct"]
            team_score = max(0, 100 - no_team_pct * 2)  # Penalizar jugadores sin equipo
            score_components.append(team_score * 0.3)  # 30% del score
        
        if not score_components:
            return 50.0  # Score neutro si no hay datos
        
        return round(sum(score_components) / len(score_components), 1)

    def generate_matching_report(
        self, matching_results: Dict[str, List[Dict]], season: str
    ) -> Dict[str, any]:
        """
        Genera reporte de resultados de matching.
        
        Args:
            matching_results: Resultados del matching
            season: Temporada procesada
            
        Returns:
            Reporte de matching
        """
        logger.info(f"📋 Generando reporte de matching para {season}")
        
        report = {
            "season": season,
            "matching_summary": {},
            "details": matching_results,
            "recommendations": []
        }
        
        # Resumen numérico
        exact_count = len(matching_results.get("exact_matches", []))
        fuzzy_count = len(matching_results.get("fuzzy_matches", []))
        no_match_count = len(matching_results.get("no_matches", []))
        multiple_count = len(matching_results.get("multiple_matches", []))
        total_count = exact_count + fuzzy_count + no_match_count + multiple_count
        
        report["matching_summary"] = {
            "total_processed": total_count,
            "exact_matches": exact_count,
            "fuzzy_matches": fuzzy_count,
            "no_matches": no_match_count,
            "multiple_matches": multiple_count,
            "success_rate_pct": round(((exact_count + fuzzy_count) / total_count * 100), 1) if total_count > 0 else 0
        }
        
        # Recomendaciones
        recommendations = []
        
        if no_match_count > 0:
            recommendations.append(f"Revisar {no_match_count} jugadores sin matching - posibles nuevos profesionales")
        
        if multiple_count > 0:
            recommendations.append(f"Resolver {multiple_count} matchings múltiples manualmente")
        
        if fuzzy_count > exact_count:
            recommendations.append("Alto número de fuzzy matches - considerar mejorar datos de referencia")
        
        report["recommendations"] = recommendations
        
        return report