# 🔍 Data Understanding - Comprensión de Datos

## Propósito
Módulo para **análisis exploratorio** y comprensión profunda de los datos antes del procesamiento y modelado.

## Componentes

### 📊 Notebooks
- **Jupyter Notebooks**: Análisis exploratorio interactivo
- **Análisis de Distribuciones**: Patrones por posición, edad, temporada
- **Detección de Anomalías**: Valores atípicos y datos inconsistentes
- **Visualizaciones**: Gráficos para entender la estructura de datos

## Objetivos del Análisis

### 🎯 Preguntas Clave
1. **Distribución de Posiciones**: ¿Cómo se distribuyen los 27 roles específicos?
2. **Calidad de Datos**: ¿Qué porcentaje de missing values por columna?
3. **Patrones Temporales**: ¿Hay evolución entre temporadas?
4. **Correlaciones**: ¿Qué métricas están más correlacionadas?
5. **Outliers**: ¿Qué jugadores tienen valores extremos?

### 📈 Análisis Típicos
- **EDA Básico**: Estadísticas descriptivas, histogramas, boxplots
- **Análisis por Posición**: Métricas específicas por grupo de posición
- **Series Temporales**: Evolución de performance por temporada
- **Análisis de Missing Values**: Estrategias de imputación

## Flujo de Trabajo

### 1. Carga de Datos
```python
import pandas as pd
from ml_system.data_acquisition.extractors import ThaiLeagueExtractor

# Cargar datos para análisis
extractor = ThaiLeagueExtractor()
dfs = []
for season in extractor.AVAILABLE_SEASONS.keys():
    success, df, _ = extractor.download_season_data(season)
    if success:
        df['season'] = season
        dfs.append(df)

df_complete = pd.concat(dfs, ignore_index=True)
```

### 2. Análisis Exploratorio
- Distribución de variables numéricas
- Frecuencia de variables categóricas
- Detección de patrones y anomalías
- Correlaciones entre métricas

### 3. Insights para Procesamiento
- Identificar variables relevantes para ML
- Definir estrategias de limpieza
- Establecer thresholds para outliers
- Planificar feature engineering

## Outputs
- **Notebooks**: Documentación del análisis exploratorio
- **Visualizaciones**: Gráficos y plots para reportes
- **Insights**: Recomendaciones para fases posteriores
- **Data Profiling**: Resumen estadístico completo

## Flujo CRISP-DM
Esta fase es el núcleo de **Data Understanding** en CRISP-DM:
- Exploración inicial de datos
- Verificación de calidad
- Identificación de problemas de datos
- Formulación de hipótesis para modeling

## Próximos Pasos
Los insights obtenidos guían la fase de **Data Processing** para limpieza y transformación óptima.
