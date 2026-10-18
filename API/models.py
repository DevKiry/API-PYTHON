from sqlalchemy import Column, Integer, String

from database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False, index=True)
    telefone = Column(String(20), nullable=True, index=True)
    email = Column(String(150), nullable=True)
    documento = Column(String(20), nullable=True, unique=True)  # CPF ou CNPJ
    endereco = Column(String(255), nullable=True)
    status = Column(String(15), nullable=False, default="ativo")  # ativo | desativado
