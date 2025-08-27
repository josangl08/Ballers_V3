# models/base.py
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base para todos los modelos."""
    
    # Configuración de tipos para enum - usar valores en lugar de nombres
    type_annotation_map = {
        # SessionStatus se importa más adelante para evitar circular import
    }
