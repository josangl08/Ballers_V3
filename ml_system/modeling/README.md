# 🤖 Modeling - Modelado de Machine Learning

## Propósito
Módulo para **entrenamiento y desarrollo** de modelos de machine learning para predicción de PDI.

## Componentes

### 🏆 Models
- **`hybrid_sklearn_model.py`**: Modelo híbrido principal usando solo scikit-learn
  - Arquitectura híbrida innovadora sin deep learning
  - 4 modelos especializados por posición (GK, DEF, MID, FWD)
  - Sistema de ensemble inteligente
  - Feature engineering avanzado (PCA + Selection)

## Arquitectura del Modelo Híbrido

### 🎯 Componentes Principales
1. **Shared Feature Processing**: Procesamiento universal
   - StandardScaler para normalización
   - PCA manteniendo 95% varianza
   - SelectKBest para top 20 features

2. **Position-Specific Models**: Modelos especializados
   - RandomForest por defecto (n_estimators=100)
   - Modelos independientes para cada grupo de posición
   - Escalado específico por posición

3. **Hybrid Ensemble**: Combinación inteligente
   - GradientBoostingRegressor como meta-modelo
   - Combina predicciones de componentes universal y específicos
   - Optimización automática de pesos

### 🔧 Configuración
```python
from ml_system.modeling.models import HybridSklearnModel, create_hybrid_sklearn_pipeline

# Crear modelo con configuración por defecto
model = create_hybrid_sklearn_pipeline()

# Entrenar
model.fit(X_train, y_train)

# Predicción
predictions = model.predict(X_test)

# Feature importance
importance = model.get_feature_importance()
```

### ⚙️ Configuración Avanzada
```python
config = {
    "shared_features_ratio": 0.95,    # Ratio varianza PCA
    "selected_features_k": 20,        # Top K features
    "position_model_type": "rf",      # rf, gb, ridge
    "ensemble_model": "gb",           # gradient_boost, rf
    "random_state": 42
}

model = HybridSklearnModel(config)
```

## Performance Esperado

### 🎯 Objetivos Académicos
- **MAE objetivo**: < 10.0 ✅ CUMPLIDO
- **R² objetivo**: > 0.60 ✅ CUMPLIDO
- **Interpretabilidad**: Feature importance disponible
- **Escalabilidad**: Maneja 2,359 registros eficientemente

### 📊 Resultados Típicos
- **Modelo Híbrido**: MAE ≈ 4.3, R² ≈ 0.74
- **RandomForest baseline**: MAE ≈ 4.1, R² ≈ 0.77
- **Ridge baseline**: MAE ≈ 5.6, R² ≈ 0.58

## Características Técnicas

### ✅ Ventajas del Sistema
- **Solo scikit-learn**: Sin dependencias complejas
- **4 posiciones**: Simplificado y manejable
- **Robusto**: Manejo de datos problemáticos
- **Interpretable**: Feature importance y análisis
- **Académico**: Metodología CRISP-DM rigurosa

### 🔄 Proceso de Entrenamiento
1. **Validación entrada**: Verificar columnas requeridas
2. **Mapeo posiciones**: 27 → 4 grupos automático
3. **Procesamiento compartido**: PCA + Feature selection
4. **Modelos por posición**: Entrenamiento especializado
5. **Ensemble final**: Meta-modelo combinando predicciones

### 📈 Evaluación
```python
from ml_system.modeling.models import evaluate_hybrid_model

# Evaluación completa
metrics = evaluate_hybrid_model(model, X_test, y_test)
# Returns: {'mae': float, 'rmse': float, 'r2': float, 'mape': float}
```

## Flujo CRISP-DM
Esta fase es el núcleo de **Modeling** en CRISP-DM:
- Selección de técnicas de modeling
- Generación de diseño de test
- Construcción del modelo
- Evaluación del modelo

## Próximos Pasos
Los modelos entrenados pasan a la fase de **Evaluation** para análisis detallado de performance y validación académica.
