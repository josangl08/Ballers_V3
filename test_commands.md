# Comandos de Testing - Ballers App

## Instalación de dependencias de testing
```bash
pip install pytest pytest-cov pytest-mock
```

## Comandos básicos

### Ejecutar todos los tests
```bash
pytest
```

### Ejecutar tests con más detalle
```bash
pytest -v
```

### Ejecutar solo tests críticos
```bash
pytest -m critical
```

### Ejecutar tests de autenticación
```bash
pytest tests/test_auth.py
```

### Ejecutar tests de base de datos
```bash
pytest tests/test_database.py
```

### Ejecutar un test específico
```bash
pytest tests/test_auth.py::TestAuthController::test_admin_login_success
```

## Tests con cobertura

### Generar reporte de cobertura
```bash
pytest --cov=controllers --cov=models --cov=common
```

### Generar reporte HTML de cobertura
```bash
pytest --cov=controllers --cov=models --cov=common --cov-report=html
```

### Ver reporte en navegador
```bash
open htmlcov/index.html
```

## Tests para migración

### Ejecutar tests críticos antes de migrar
```bash
pytest -m critical -v
```

### Ejecutar tests después de migrar a Dash
```bash
pytest -v  # Todos deben pasar igual
```

## Debug de tests

### Ejecutar test con debug detallado
```bash
pytest tests/test_auth.py::test_admin_login_success -v -s
```

### Parar en primer error
```bash
pytest -x
```

### Ver variables locales en errores
```bash
pytest -l
```