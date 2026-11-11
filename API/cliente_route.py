from enum import Enum
from typing import Dict, Iterable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import STATUS_CANCELADO, Cliente, Pedido, get_db
 
clientes_router = APIRouter(prefix="/clientes", tags=["Cliente"])
 
 
# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StatusCliente(str, Enum):
    ativo = "ativo"
    desativado = "desativado"
 
 
class ClienteIn(BaseModel):
    nome: str
    telefone: str
    email: str
    documento: str
    endereco: str
 
 
class ClienteOut(ClienteIn):
    id: int
    status: StatusCliente = StatusCliente.ativo
    # Pedidos não cancelados do cliente (usado pelo app nas listas e relatórios).
    total_pedidos: int = 0
 
 
class StatusIn(BaseModel):
    status: StatusCliente
 
 
# ---------------------------------------------------------------------------
# Helpers (banco guarda status como Boolean; a API expõe "ativo"/"desativado")
# ---------------------------------------------------------------------------
def contar_pedidos(session: Session, ids: Iterable[int]) -> Dict[int, int]:
    """Quantidade de pedidos não cancelados por cliente (1 consulta só)."""
    ids = list(ids)
    if not ids:
        return {}
    linhas = (
        session.query(Pedido.cliente_id, func.count(Pedido.id))
        .filter(Pedido.cliente_id.in_(ids), Pedido.status != STATUS_CANCELADO)
        .group_by(Pedido.cliente_id)
        .all()
    )
    return {cliente_id: total for cliente_id, total in linhas}


def to_out(c: Cliente, total_pedidos: int = 0) -> ClienteOut:
    return ClienteOut(
        id=c.id,
        nome=c.nome,
        telefone=c.telefone,
        email=c.email,
        documento=c.documento,
        endereco=c.endereco,
        status=StatusCliente.ativo if c.status else StatusCliente.desativado,
        total_pedidos=total_pedidos,
    )


def to_out_session(session: Session, c: Cliente) -> ClienteOut:
    return to_out(c, contar_pedidos(session, [c.id]).get(c.id, 0))


def buscar_ou_404(session: Session, id: int) -> Cliente:
    cliente = session.get(Cliente, id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


# ---------------------------------------------------------------------------
# POST /clientes/cadastrar
# ---------------------------------------------------------------------------
@clientes_router.post("/cadastrar", status_code=201, response_model=ClienteOut)
def cadastrar_cliente(cliente: ClienteIn, session: Session = Depends(get_db)):
    novo = Cliente(**cliente.model_dump())
    session.add(novo)
    session.commit()
    session.refresh(novo)
    return to_out_session(session, novo)


# ---------------------------------------------------------------------------
# GET /clientes/consultar  (um único GET)
#
#   /clientes/consultar                         -> todos os clientes
#   /clientes/consultar?id=1                    -> só o cliente 1
#   /clientes/consultar?id_inicial=10&id_final=30
#                                               -> clientes com id de 10 a 30
#   /clientes/consultar?id_inicial=10&limite=20 -> 20 clientes a partir do id 10
#   /clientes/consultar?busca=Maria             -> filtra por nome ou telefone
# ---------------------------------------------------------------------------
@clientes_router.get("/consultar")
def consultar_clientes(
    id: Optional[int] = Query(None, description="Se informado, retorna só esse cliente"),
    id_inicial: Optional[int] = Query(None, ge=1, description="Começa a partir deste ID (inclusive)"),
    id_final: Optional[int] = Query(None, ge=1, description="Termina neste ID (inclusive)"),
    limite: int = Query(20, ge=1, le=100, description="Máximo de resultados"),
    busca: Optional[str] = Query(None, description="Pesquisa por nome ou telefone"),
    session: Session = Depends(get_db),
):
    # Com id: consulta apenas aquele cliente
    if id is not None:
        return to_out_session(session, buscar_ou_404(session, id))

    if id_inicial is not None and id_final is not None and id_inicial > id_final:
        raise HTTPException(status_code=400, detail="id_inicial não pode ser maior que id_final")

    consulta = session.query(Cliente)

    if id_inicial is not None:
        consulta = consulta.filter(Cliente.id >= id_inicial)
    if id_final is not None:
        consulta = consulta.filter(Cliente.id <= id_final)
    if busca:
        consulta = consulta.filter(
            or_(Cliente.nome.ilike(f"%{busca}%"), Cliente.telefone.contains(busca))
        )

    resultado = consulta.order_by(Cliente.id).limit(limite).all()
    totais = contar_pedidos(session, [c.id for c in resultado])

    return {
        "total_retornado": len(resultado),
        "proximo_id_inicial": resultado[-1].id + 1 if len(resultado) == limite else None,
        "clientes": [to_out(c, totais.get(c.id, 0)) for c in resultado],
    }


# ---------------------------------------------------------------------------
# PUT /clientes/editar/{id}
# ---------------------------------------------------------------------------
@clientes_router.put("/editar/{id}", response_model=ClienteOut)
def editar_cliente(id: int, dados: ClienteIn, session: Session = Depends(get_db)):
    cliente = buscar_ou_404(session, id)
    for campo, valor in dados.model_dump().items():
        setattr(cliente, campo, valor)
    session.commit()
    session.refresh(cliente)
    return to_out_session(session, cliente)


# ---------------------------------------------------------------------------
# PATCH /clientes/status/{id}  (ativo / desativado)
# ---------------------------------------------------------------------------
@clientes_router.patch("/status/{id}", response_model=ClienteOut)
def atualizar_status(id: int, dados: StatusIn, session: Session = Depends(get_db)):
    cliente = buscar_ou_404(session, id)
    cliente.status = dados.status == StatusCliente.ativo
    session.commit()
    session.refresh(cliente)
    return to_out_session(session, cliente)


# ---------------------------------------------------------------------------
# DELETE /clientes/excluir/{id}  (exclusão lógica: preserva o histórico)
# ---------------------------------------------------------------------------
@clientes_router.delete("/excluir/{id}")
def excluir_cliente(id: int, session: Session = Depends(get_db)):
    cliente = buscar_ou_404(session, id)
    cliente.status = False
    session.commit()
    return {"mensagem": "Cliente desativado (exclusão lógica)", "id": id}
