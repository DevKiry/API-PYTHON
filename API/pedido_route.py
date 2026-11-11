from datetime import date
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from models import (
    GRADE_LETRAS,
    GRADE_NUMEROS,
    Cliente,
    ItemPedido,
    Pedido,
    get_db,
)

pedidos_router = APIRouter(prefix="/pedidos", tags=["Pedido"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StatusPedido(str, Enum):
    recebido = "recebido"
    em_producao = "em_producao"
    concluido = "concluido"
    entregue = "entregue"
    cancelado = "cancelado"


class ItemPedidoIn(BaseModel):
    referencia: str
    modelo: str
    tecido: str
    cor: str
    # Quantidade por tamanho: 5 posições (PP..GG) ou 8 posições (36..50).
    quantidades: List[int]
    valor_unitario: float = Field(0, ge=0)

    @field_validator("quantidades")
    @classmethod
    def validar_grade(cls, valor: List[int]) -> List[int]:
        if len(valor) not in (len(GRADE_LETRAS), len(GRADE_NUMEROS)):
            raise ValueError(
                f"A grade deve ter {len(GRADE_LETRAS)} ou {len(GRADE_NUMEROS)} tamanhos"
            )
        if any(q < 0 for q in valor):
            raise ValueError("As quantidades não podem ser negativas")
        return valor


class ItemPedidoOut(ItemPedidoIn):
    id: int
    total_pecas: int
    valor_total: float


class PedidoBase(BaseModel):
    cliente_id: int
    data_pedido: date
    observacoes: Optional[str] = None


class PedidoIn(PedidoBase):
    # Na criação, ausente = pedido sem itens.
    # Na edição, ausente = mantém os itens atuais (lista enviada = substitui).
    itens: Optional[List[ItemPedidoIn]] = None


class StatusPedidoIn(BaseModel):
    status: StatusPedido


class PedidoOut(PedidoBase):
    id: int
    status: StatusPedido = StatusPedido.recebido
    cliente_nome: Optional[str] = None
    itens: List[ItemPedidoOut] = []
    total_pecas: int = 0
    valor_total: float = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pedido_para_out(pedido: Pedido) -> PedidoOut:
    """Converte o registro do banco no formato devolvido pela API."""
    itens = [
        ItemPedidoOut(
            id=i.id,
            referencia=i.referencia,
            modelo=i.modelo,
            tecido=i.tecido,
            cor=i.cor,
            quantidades=list(i.quantidades),
            valor_unitario=float(i.valor_unitario or 0),
            total_pecas=i.quantidade_total,
            valor_total=round(i.quantidade_total * float(i.valor_unitario or 0), 2),
        )
        for i in pedido.itens
    ]
    return PedidoOut(
        id=pedido.id,
        cliente_id=pedido.cliente_id,
        cliente_nome=pedido.cliente.nome if pedido.cliente else None,
        data_pedido=pedido.data_pedido,
        observacoes=pedido.observacoes,
        status=StatusPedido(pedido.status),
        itens=itens,
        total_pecas=sum(i.total_pecas for i in itens),
        valor_total=round(sum(i.valor_total for i in itens), 2),
    )


def montar_itens(itens: List[ItemPedidoIn]) -> List[ItemPedido]:
    return [ItemPedido(**item.model_dump()) for item in itens]


def buscar_pedido_ou_404(session: Session, id: int) -> Pedido:
    pedido = session.get(Pedido, id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido


def validar_cliente_ativo(session: Session, cliente_id: int, mensagem_inativo: str) -> Cliente:
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if not cliente.status:
        raise HTTPException(status_code=400, detail=mensagem_inativo)
    return cliente


# ---------------------------------------------------------------------------
# POST /pedidos/cadastrar
# ---------------------------------------------------------------------------
@pedidos_router.post("/cadastrar", status_code=201, response_model=PedidoOut)
def criar_pedido(pedido: PedidoIn, session: Session = Depends(get_db)):
    validar_cliente_ativo(
        session,
        pedido.cliente_id,
        "Não é possível criar pedido para um cliente desativado",
    )

    novo = Pedido(
        cliente_id=pedido.cliente_id,
        data_pedido=pedido.data_pedido,
        observacoes=pedido.observacoes,
        status=StatusPedido.recebido.value,
    )
    novo.itens = montar_itens(pedido.itens or [])
    session.add(novo)
    session.commit()
    session.refresh(novo)
    return pedido_para_out(novo)


# ---------------------------------------------------------------------------
# GET /pedidos/consultar
# ---------------------------------------------------------------------------
@pedidos_router.get("/consultar")
def consultar_pedidos(
    id: Optional[int] = Query(None, description="ID de um pedido específico"),
    cliente_id: Optional[int] = Query(None, ge=1, description="Filtrar pedidos pelo ID do cliente"),
    session: Session = Depends(get_db),
):
    if id is not None:
        return pedido_para_out(buscar_pedido_ou_404(session, id))

    consulta = session.query(Pedido)
    if cliente_id is not None:
        consulta = consulta.filter(Pedido.cliente_id == cliente_id)

    resultado = consulta.order_by(Pedido.id).all()

    return {
        "total_retornado": len(resultado),
        "pedidos": [pedido_para_out(p) for p in resultado],
    }


# ---------------------------------------------------------------------------
# PUT /pedidos/editar/{id}
# ---------------------------------------------------------------------------
@pedidos_router.put("/editar/{id}", response_model=PedidoOut)
def editar_pedido(id: int, dados: PedidoIn, session: Session = Depends(get_db)):
    pedido = buscar_pedido_ou_404(session, id)

    validar_cliente_ativo(
        session,
        dados.cliente_id,
        "Não é possível vincular um pedido a um cliente desativado",
    )

    pedido.cliente_id = dados.cliente_id
    pedido.data_pedido = dados.data_pedido
    pedido.observacoes = dados.observacoes
    if dados.itens is not None:
        pedido.itens = montar_itens(dados.itens)

    session.commit()
    session.refresh(pedido)
    return pedido_para_out(pedido)


# ---------------------------------------------------------------------------
# PATCH /pedidos/status/{id}
# ---------------------------------------------------------------------------
@pedidos_router.patch("/status/{id}", response_model=PedidoOut)
def alterar_status_pedido(id: int, dados: StatusPedidoIn, session: Session = Depends(get_db)):
    pedido = buscar_pedido_ou_404(session, id)
    pedido.status = dados.status.value
    session.commit()
    session.refresh(pedido)
    return pedido_para_out(pedido)


# ---------------------------------------------------------------------------
# DELETE /pedidos/excluir/{id}  (exclusão lógica: marca como cancelado)
# ---------------------------------------------------------------------------
@pedidos_router.delete("/excluir/{id}")
def excluir_pedido(id: int, session: Session = Depends(get_db)):
    pedido = buscar_pedido_ou_404(session, id)
    pedido.status = StatusPedido.cancelado.value
    session.commit()

    return {
        "mensagem": "Pedido cancelado com sucesso",
        "id": id,
        "status": StatusPedido.cancelado,
    }
