# 📥 Data Acquisition - Adquisición de Datos

## Propósito
Módulo responsable de la **extracción y adquisición** de datos desde fuentes externas para el sistema ML.

## Componentes

### 🔌 Extractors
- **`thai_league_extractor.py`**: Extractor principal para datos de Thai League desde GitHub
  - Descarga automática desde repositorio Wyscout_Prospect_Research
  - Sistema de cache local para optimizar descargas
  - Manejo de 5 temporadas (2020-2025)
  - Validación básica de datos descargados

## Uso

### Extracción Básica
```python
from ml_system.data_acquisition.extractors import ThaiLeagueExtractor

# Inicializar extractor
extractor = ThaiLeagueExtractor()

# Descargar temporada específica
success, df, message = extractor.download_season_data("2024-25")

# Descargar todas las temporadas
for season in extractor.AVAILABLE_SEASONS.keys():
    success, df, message = extractor.download_season_data(season)
```

## Outputs
- **Datos Raw**: Almacenados en `data/thai_league_raw/`
- **Cache Local**: Sistema de cache automático para evitar descargas duplicadas
- **DataFrames**: Retorna pandas DataFrames listos para procesamiento

## Flujo CRISP-DM
Esta fase corresponde a **Data Understanding** en metodología CRISP-DM:
- Adquisición de datos de fuentes confiables
- Verificación de disponibilidad y calidad inicial
- Establecimiento de cache para reproducibilidad

## Próximos Pasos
Los datos extraídos pasan a la fase de **Data Processing** para limpieza y transformación.
