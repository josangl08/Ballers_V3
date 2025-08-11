# 🧹 Data Processing - Procesamiento de Datos

## Propósito
Módulo para **limpieza, transformación y preparación** de datos para machine learning.

## Componentes

### 🔧 Processors
- **`simple_data_processor.py`**: Pipeline principal de procesamiento simplificado
  - Limpieza básica sin validaciones estrictas
  - Generación de CSV procesados listos para ML
  - Manejo robusto de errores y datos problemáticos

- **`position_mapper.py`**: Sistema de mapeo de posiciones
  - Mapeo inteligente: 27 posiciones específicas → 4 grupos principales
  - Análisis de distribución por posición
  - Validación de cobertura de mapeo

## Funcionalidades Principales

### 🎯 Mapeo de Posiciones (27 → 4)
```python
from ml_system.data_processing.processors import position_mapper, map_position

# Mapeo individual
group = map_position("LCMF")  # Returns: "MID"

# Análisis de distribución
positions = ["GK", "CB", "LCMF", "CF", "LW"]
analysis = position_mapper.analyze_position_distribution(positions)
```

**Grupos Principales:**
- **GK** (8%): Porteros
- **DEF** (35%): Defensas (CB, LB, RB, LCB, RCB, LWB, RWB, etc.)
- **MID** (40%): Mediocampistas (DMF, CMF, AMF, LCMF, RCMF, etc.)
- **FWD** (17%): Delanteros (CF, LW, RW, LWF, RWF, SS)

### 🧹 Procesamiento Simple
```python
from ml_system.data_processing.processors.simple_data_processor import process_all_seasons

# Ejecutar pipeline completo
results = process_all_seasons()
# Genera CSV procesados en data/thai_league_processed/
```

**Pipeline de Procesamiento:**
1. **Carga datos raw** desde extractor
2. **Limpieza básica** sin validaciones estrictas
3. **Mapeo de posiciones** 27 → 4 grupos
4. **Feature engineering básico** (PDI calculation)
5. **Guardado CSV procesados** listos para ML

## Features Generadas

### 🎯 PDI (Player Development Index)
- **Escala**: 30-100 (como rating FIFA)
- **Cálculo**: Promedio normalizado de features clave
- **Ajustes**: Factor edad, ruido realista
- **Distribución**: Balanceada por posición

### 📊 Metadatos
- `processing_date`: Timestamp de procesamiento
- `data_source`: "simple_processor"
- `ml_features_applied`: Boolean flag
- `Position_Group`: Grupo mapeado (GK/DEF/MID/FWD)

## Outputs

### 📁 CSV Procesados
**Ubicación**: `data/thai_league_processed/`
- `processed_2020-21.csv` (~0.3 MB)
- `processed_2021-22.csv` (~0.3 MB)
- `processed_2022-23.csv` (~0.3 MB)
- `processed_2023-24.csv` (~0.3 MB)
- `processed_2024-25.csv` (~0.3 MB)
- `processed_complete.csv` (~1.5 MB) - **Dataset consolidado**

### ✅ Calidad de Datos
- **Total registros**: 2,359 jugadores
- **Temporadas**: 5 (2020-2025)
- **Missing values**: Manejados con estrategia robusta
- **Outliers**: Límites sensatos aplicados
- **Consistencia**: Posiciones validadas y mapeadas

## Flujo CRISP-DM
Esta fase corresponde a **Data Preparation** en CRISP-DM:
- Limpieza de datos problemáticos
- Transformación de variables categóricas
- Feature engineering inicial
- Preparación para modeling

## Próximos Pasos
Los CSV procesados alimentan directamente la fase de **Modeling** con datos limpios y estructurados.
