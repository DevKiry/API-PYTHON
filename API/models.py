import os
from datetime import date
from typing import Iterator, List, Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

load_dotenv()

# Configuração via variáveis de ambiente (arquivo .env).
# Se não existirem, usa os valores padrão abaixo.
DB_USER = os.getenv("DB_USER", "casaos")
DB_PASSWORD = os.getenv("DB_PASSWORD", "casaos")
DB_HOST = os.getenv("DB_HOST", "10.57.223.221")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

db = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=db, autoflush=False)

Base = declarative_base()

# Status usado em vários módulos (valor gravado em pedidos.status).
STATUS_CANCELADO = "cancelado"

# Grades de tamanho aceitas nos itens do pedido (mesmas do app Flutter).
GRADE_LETRAS = ["PP", "P", "M", "G", "GG"]
GRADE_NUMEROS = ["36", "38", "40", "42", "44", "46", "48", "50"]


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: abre uma sessão por requisição e fecha no final."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# CLIENTES
# ---------------------------------------------------------------------------
class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    nome = Column(String, nullable=False)
    telefone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    documento = Column(String, nullable=False)
    endereco = Column(String, nullable=False)

    status = Column(Boolean, default=True)  # True = ativo, False = desativado

    def __init__(
        self,
        nome: str,
        telefone: str,
        email: str,
        documento: str,
        endereco: str,
    ) -> None:
        self.nome = nome
        self.telefone = telefone
        self.email = email
        self.documento = documento
        self.endereco = endereco
        self.status = True


# ---------------------------------------------------------------------------
# PEDIDOS
# ---------------------------------------------------------------------------
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    cliente_id = Column(
        Integer, ForeignKey("clientes.id"), nullable=False, index=True
    )
    data_pedido = Column(Date, nullable=False)
    observacoes = Column(String, nullable=True)

    # Guarda o valor do enum StatusPedido (ver pedido_route.py)
    status = Column(String, nullable=False, default="recebido")

    cliente = relationship("Cliente", lazy="joined")
    itens = relationship(
        "ItemPedido",
        cascade="all, delete-orphan",
        order_by="ItemPedido.id",
        lazy="selectin",
    )

    def __init__(
        self,
        cliente_id: int,
        data_pedido: date,
        observacoes: Optional[str] = None,
        status: str = "recebido",
    ) -> None:
        self.cliente_id = cliente_id
        self.data_pedido = data_pedido
        self.observacoes = observacoes
        self.status = status


class ItemPedido(Base):
    """Item de um pedido: uma peça (modelo/tecido/cor) com a grade de tamanhos."""

    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    pedido_id = Column(
        Integer, ForeignKey("pedidos.id"), nullable=False, index=True
    )
    referencia = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    tecido = Column(String, nullable=False)
    cor = Column(String, nullable=False)

    # Quantidade por tamanho, na ordem da grade (5 posições = PP..GG,
    # 8 posições = 36..50).
    quantidades = Column(JSON, nullable=False)
    # Soma de `quantidades` (gravada para permitir somar peças direto no SQL).
    quantidade_total = Column(Integer, nullable=False, default=0)
    valor_unitario = Column(Numeric(10, 2, asdecimal=False), nullable=False, default=0)

    def __init__(
        self,
        referencia: str,
        modelo: str,
        tecido: str,
        cor: str,
        quantidades: List[int],
        valor_unitario: float = 0,
    ) -> None:
        self.referencia = referencia
        self.modelo = modelo
        self.tecido = tecido
        self.cor = cor
        self.quantidades = list(quantidades)
        self.quantidade_total = sum(quantidades)
        self.valor_unitario = valor_unitario


# ---------------------------------------------------------------------------
# RELATÓRIOS (usam as tabelas acima; não possuem tabela própria)
# ---------------------------------------------------------------------------


def criar_tabelas() -> None:
    Base.metadata.create_all(bind=db)
