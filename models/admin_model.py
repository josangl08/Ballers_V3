from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from .user_model import Base

class Admin(Base):
    __tablename__ = "admins"

    admin_id = Column(Integer, primary_key=True)
    user_id  = Column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    role     = Column(String)     # Descripción de rol interno si hiciera falta

    # Relaciones
    user     = relationship("User", back_populates="admin_profile")