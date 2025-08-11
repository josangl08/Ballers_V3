#!/usr/bin/env python3
"""
Position Mapper - Mapeo de posiciones detalladas a grupos principales
Sistema para simplificar 27+ posiciones específicas a 4 grupos principales.

Este módulo agrupa las posiciones específicas de Wyscout en 4 categorías principales:
- GK: Porteros
- DEF: Defensas (centrales, laterales, líberos)
- MID: Mediocampistas (defensivos, centrales, ofensivos)
- FWD: Delanteros (extremos, centrodelanteros, segundos puntas)

Mantiene la posición específica como metadato pero entrena modelos con grupos principales.

Autor: Proyecto Fin de Máster - Python Aplicado al Deporte
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Mapeo detallado de posiciones específicas a grupos principales
POSITION_MAPPING = {
    # PORTEROS
    "GK": "GK",
    # DEFENSAS
    "CB": "DEF",  # Central Back
    "LCB": "DEF",  # Left Centre-Back
    "RCB": "DEF",  # Right Centre-Back
    "LCB3": "DEF",  # Left Centre-Back in 3-back
    "RCB3": "DEF",  # Right Centre-Back in 3-back
    "LB": "DEF",  # Left Back
    "RB": "DEF",  # Right Back
    "LB5": "DEF",  # Left Back in 5-back
    "RB5": "DEF",  # Right Back in 5-back
    "LWB": "DEF",  # Left Wing-Back
    "RWB": "DEF",  # Right Wing-Back
    # MEDIOCAMPISTAS
    "DMF": "MID",  # Defensive Midfielder
    "LDMF": "MID",  # Left Defensive Midfielder
    "RDMF": "MID",  # Right Defensive Midfielder
    "CMF": "MID",  # Centre Midfielder
    "LCMF": "MID",  # Left Centre Midfielder
    "RCMF": "MID",  # Right Centre Midfielder
    "LCMF3": "MID",  # Left Centre Midfielder in 3-man midfield
    "RCMF3": "MID",  # Right Centre Midfielder in 3-man midfield
    "AMF": "MID",  # Attacking Midfielder
    "LAMF": "MID",  # Left Attacking Midfielder
    "RAMF": "MID",  # Right Attacking Midfielder
    # DELANTEROS
    "LW": "FWD",  # Left Winger
    "RW": "FWD",  # Right Winger
    "LWF": "FWD",  # Left Wing Forward
    "RWF": "FWD",  # Right Wing Forward
    "CF": "FWD",  # Centre Forward
    "SS": "FWD",  # Second Striker
    # FALLBACKS para posiciones no mapeadas
    "Unknown": "MID",  # Asignar a MID por defecto
}

# Descripciones de los grupos principales
GROUP_DESCRIPTIONS = {
    "GK": {
        "name": "Portero",
        "description": "Guardametas y arqueros",
        "key_attributes": ["reflexes", "positioning", "distribution", "aerial_ability"],
        "typical_positions": ["GK"],
    },
    "DEF": {
        "name": "Defensa",
        "description": "Defensas centrales, laterales y líberos",
        "key_attributes": [
            "defensive_duels",
            "aerial_duels",
            "interceptions",
            "tackles",
        ],
        "typical_positions": ["CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"],
    },
    "MID": {
        "name": "Mediocampista",
        "description": "Mediocampistas defensivos, centrales y ofensivos",
        "key_attributes": ["pass_accuracy", "dribbles", "key_passes", "duels_won"],
        "typical_positions": ["DMF", "CMF", "AMF", "LCMF", "RCMF"],
    },
    "FWD": {
        "name": "Delantero",
        "description": "Extremos, centrodelanteros y segundos puntas",
        "key_attributes": ["goals", "assists", "shots", "dribbles", "speed"],
        "typical_positions": ["CF", "LW", "RW", "LWF", "RWF", "SS"],
    },
}

# Estadísticas de distribución esperada (aproximada)
EXPECTED_DISTRIBUTION = {
    "GK": 0.08,  # ~8% porteros
    "DEF": 0.35,  # ~35% defensas
    "MID": 0.40,  # ~40% mediocampistas
    "FWD": 0.17,  # ~17% delanteros
}


class PositionMapper:
    """
    Mapeador de posiciones específicas a grupos principales.

    Funcionalidades:
    - Mapeo automático de posición específica a grupo
    - Validación de distribución
    - Análisis de cobertura de mapeo
    - Metadatos de grupos
    """

    def __init__(self):
        """Inicializa el mapeador con configuración por defecto."""
        self.position_mapping = POSITION_MAPPING.copy()
        self.group_descriptions = GROUP_DESCRIPTIONS.copy()
        self.unmapped_positions = set()

        logger.info("PositionMapper inicializado con 4 grupos principales")

    def map_position(self, specific_position: str) -> str:
        """
        Mapea una posición específica a grupo principal.

        Args:
            specific_position: Posición específica (ej: "LCMF")

        Returns:
            Grupo principal (ej: "MID")
        """
        if not specific_position or specific_position.strip() == "":
            return "MID"  # Default

        # Limpiar posición
        position_clean = specific_position.strip().upper()

        # Buscar mapeo directo
        if position_clean in self.position_mapping:
            return self.position_mapping[position_clean]

        # Buscar mapeo parcial (para casos como "Centre-Back" → "CB")
        for mapped_pos, group in self.position_mapping.items():
            if mapped_pos in position_clean or position_clean in mapped_pos:
                return group

        # Si no se encuentra, registrar como no mapeado y asignar MID
        if position_clean not in self.unmapped_positions:
            self.unmapped_positions.add(position_clean)
            logger.warning(f"Posición no mapeada: '{position_clean}' → asignada a MID")

        return "MID"  # Default fallback

    def map_positions_batch(self, positions: List[str]) -> List[str]:
        """
        Mapea una lista de posiciones específicas a grupos principales.

        Args:
            positions: Lista de posiciones específicas

        Returns:
            Lista de grupos principales
        """
        return [self.map_position(pos) for pos in positions]

    def get_group_info(self, group: str) -> Optional[Dict]:
        """
        Obtiene información detallada de un grupo principal.

        Args:
            group: Grupo principal (GK, DEF, MID, FWD)

        Returns:
            Dict con información del grupo o None
        """
        return self.group_descriptions.get(group)

    def analyze_position_distribution(self, positions: List[str]) -> Dict[str, any]:
        """
        Analiza la distribución de posiciones en un dataset.

        Args:
            positions: Lista de posiciones específicas

        Returns:
            Dict con análisis de distribución
        """
        # Mapear a grupos principales
        mapped_groups = self.map_positions_batch(positions)

        # Contar distribución
        group_counts = {}
        for group in ["GK", "DEF", "MID", "FWD"]:
            group_counts[group] = mapped_groups.count(group)

        total = len(positions)

        # Calcular porcentajes
        distribution = {}
        for group, count in group_counts.items():
            distribution[group] = {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0,
                "expected_percentage": EXPECTED_DISTRIBUTION[group] * 100,
            }

        return {
            "total_positions": total,
            "unique_specific_positions": len(set(positions)),
            "unique_mapped_groups": len(set(mapped_groups)),
            "distribution": distribution,
            "unmapped_positions": list(self.unmapped_positions),
            "coverage": {
                "mapped_positions": len(self.position_mapping),
                "unmapped_found": len(self.unmapped_positions),
            },
        }

    def get_positions_by_group(self, group: str) -> List[str]:
        """
        Obtiene todas las posiciones específicas que mapean a un grupo.

        Args:
            group: Grupo principal (GK, DEF, MID, FWD)

        Returns:
            Lista de posiciones específicas del grupo
        """
        return [pos for pos, grp in self.position_mapping.items() if grp == group]

    def add_position_mapping(self, specific_position: str, group: str) -> bool:
        """
        Añade un nuevo mapeo de posición específica a grupo.

        Args:
            specific_position: Posición específica a mapear
            group: Grupo principal (debe ser GK, DEF, MID, FWD)

        Returns:
            True si se añadió exitosamente, False si no
        """
        if group not in ["GK", "DEF", "MID", "FWD"]:
            logger.error(f"Grupo inválido: {group}. Debe ser GK, DEF, MID, FWD")
            return False

        self.position_mapping[specific_position.strip().upper()] = group
        logger.info(f"Mapeo añadido: {specific_position} → {group}")
        return True

    def get_mapping_summary(self) -> Dict[str, any]:
        """
        Obtiene resumen completo del sistema de mapeo.

        Returns:
            Dict con resumen del mapeo
        """
        summary = {
            "total_mappings": len(self.position_mapping),
            "groups": list(self.group_descriptions.keys()),
            "mappings_by_group": {},
        }

        for group in ["GK", "DEF", "MID", "FWD"]:
            positions = self.get_positions_by_group(group)
            summary["mappings_by_group"][group] = {
                "count": len(positions),
                "positions": positions,
                "description": self.group_descriptions[group]["name"],
            }

        return summary


# Instancia global para uso fácil
position_mapper = PositionMapper()


# Funciones de conveniencia
def map_position(position: str) -> str:
    """Función de conveniencia para mapear una posición."""
    return position_mapper.map_position(position)


def map_positions(positions: List[str]) -> List[str]:
    """Función de conveniencia para mapear múltiples posiciones."""
    return position_mapper.map_positions_batch(positions)


def get_group_info(group: str) -> Optional[Dict]:
    """Función de conveniencia para obtener info de grupo."""
    return position_mapper.get_group_info(group)


def analyze_distribution(positions: List[str]) -> Dict:
    """Función de conveniencia para analizar distribución."""
    return position_mapper.analyze_position_distribution(positions)


if __name__ == "__main__":
    # Test del sistema de mapeo
    print("🧪 Testing Position Mapper...")

    # Posiciones de prueba
    test_positions = [
        "GK",
        "CB",
        "LB",
        "RB",
        "DMF",
        "CMF",
        "AMF",
        "CF",
        "LW",
        "RW",
        "LCMF",
        "RCMF",
        "LAMF",
        "RAMF",
        "LCB",
        "RCB",
        "LWF",
        "RWF",
    ]

    mapper = PositionMapper()

    # Test mapeo individual
    print("\n📋 Mapeo individual:")
    for pos in test_positions:
        group = mapper.map_position(pos)
        print(f"   {pos:6} → {group}")

    # Test distribución
    print("\n📊 Análisis de distribución:")
    distribution = mapper.analyze_position_distribution(
        test_positions * 5
    )  # Simular dataset

    for group, stats in distribution["distribution"].items():
        print(f"   {group}: {stats['count']:2} ({stats['percentage']:4.1f}%)")

    # Test resumen
    print(f"\n✅ Sistema configurado:")
    summary = mapper.get_mapping_summary()
    print(f"   • Total mapeos: {summary['total_mappings']}")
    print(f"   • Grupos: {len(summary['groups'])}")
    for group, info in summary["mappings_by_group"].items():
        print(f"   • {group}: {info['count']} posiciones → {info['description']}")

    print("\n🎯 Position Mapper listo para uso!")
