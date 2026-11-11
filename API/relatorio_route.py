from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from models import (
    GRADE_LETRAS,
    GRADE_NUMEROS,
    STATUS_CANCELADO,
    Cliente,
    ItemPedido,
    Pedido,
    get_db,
)
from pedido_route import StatusPedido, pedido_para_out

relatorios_router = APIRouter(prefix="/relatorios", tags=["Relatórios"])

AGRUPAMENTOS_PECAS = ("modelo", "referencia", "tecido", "cor", "tamanho", "cliente")

# Soma de peças e de valor (peças x valor unitário) dos itens.
_SOMA_PECAS = func.coalesce(func.sum(ItemPedido.quantidade_total), 0)
_SOMA_VALOR = func.coalesce(
    func.sum(ItemPedido.quantidade_total * ItemPedido.valor_unitario), 0
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _filtro_periodo(consulta, mes: Optional[int], ano: Optional[int]):
    if mes is not None:
        consulta = consulta.filter(extract("month", Pedido.data_pedido) == mes)
    if ano is not None:
        consulta = consulta.filter(extract("year", Pedido.data_pedido) == ano)
    return consulta


def _totais(
    session: Session, mes: Optional[int] = None, ano: Optional[int] = None
) -> Tuple[int, int, float]:
    """(quantidade de pedidos, total de peças, valor) dos pedidos não cancelados."""
    quantidade = _filtro_periodo(
        session.query(func.count(Pedido.id)).filter(Pedido.status != STATUS_CANCELADO),
        mes,
        ano,
    ).scalar() or 0

    pecas, valor = _filtro_periodo(
        session.query(_SOMA_PECAS, _SOMA_VALOR)
        .select_from(ItemPedido)
        .join(Pedido, ItemPedido.pedido_id == Pedido.id)
        .filter(Pedido.status != STATUS_CANCELADO),
        mes,
        ano,
    ).one()
    return int(quantidade), int(pecas or 0), round(float(valor or 0), 2)


def _mes_anterior(ano: int, mes: int, voltar: int) -> Tuple[int, int]:
    indice = ano * 12 + (mes - 1) - voltar
    return indice // 12, indice % 12 + 1


# ---------------------------------------------------------
# GET /relatorios/dashboard
# Resumo geral dos clientes e pedidos
# ---------------------------------------------------------
@relatorios_router.get("/dashboard")
def dashboard(
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2000),
    session: Session = Depends(get_db),
):
    total_clientes = (
        session.query(func.count(Cliente.id)).filter(Cliente.status.is_(True)).scalar() or 0
    )

    # Pedidos não cancelados, com filtro opcional de mês e ano
    pedidos_periodo, pecas_periodo, valor_periodo = _totais(session, mes, ano)
    _, pecas_geral, _ = _totais(session)

    return {
        "total_clientes": total_clientes,
        "pedidos_no_mes": pedidos_periodo,
        "total_pecas": pecas_periodo,
        "valor_total_pedidos": valor_periodo,
        # Peças de todos os pedidos, sem filtro de período (card "Total de Peças")
        "total_pecas_geral": pecas_geral,
    }


# ---------------------------------------------------------
# GET /relatorios/faturamento
# Consulta de pedidos por período, cliente e status
# (sem o parâmetro status, pedidos cancelados não entram)
# ---------------------------------------------------------
@relatorios_router.get("/faturamento")
def faturamento(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    cliente_id: Optional[int] = Query(None, ge=1),
    status: Optional[StatusPedido] = None,
    session: Session = Depends(get_db),
):
    if data_inicio is not None and data_fim is not None and data_inicio > data_fim:
        raise HTTPException(
            status_code=400,
            detail="data_inicio não pode ser posterior a data_fim",
        )

    def aplicar_filtros(consulta):
        if data_inicio is not None:
            consulta = consulta.filter(Pedido.data_pedido >= data_inicio)
        if data_fim is not None:
            consulta = consulta.filter(Pedido.data_pedido <= data_fim)
        if cliente_id is not None:
            consulta = consulta.filter(Pedido.cliente_id == cliente_id)
        if status is not None:
            return consulta.filter(Pedido.status == status.value)
        return consulta.filter(Pedido.status != STATUS_CANCELADO)

    quantidade = aplicar_filtros(session.query(func.count(Pedido.id))).scalar() or 0
    valor = aplicar_filtros(
        session.query(_SOMA_VALOR)
        .select_from(ItemPedido)
        .join(Pedido, ItemPedido.pedido_id == Pedido.id)
    ).scalar()

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "cliente_id": cliente_id,
        "status": status,
        "quantidade_pedidos": quantidade,
        "valor_total": round(float(valor or 0), 2),
    }


# ---------------------------------------------------------
# GET /relatorios/faturamento-mensal
# Faturamento dos últimos N meses (para o gráfico de barras)
# ---------------------------------------------------------
@relatorios_router.get("/faturamento-mensal")
def faturamento_mensal(
    meses: int = Query(6, ge=1, le=24, description="Quantidade de meses retornados"),
    ate_mes: Optional[int] = Query(None, ge=1, le=12, description="Último mês (padrão: mês atual)"),
    ate_ano: Optional[int] = Query(None, ge=2000, description="Ano do último mês (padrão: ano atual)"),
    session: Session = Depends(get_db),
):
    hoje = date.today()
    fim_ano = ate_ano if ate_ano is not None else hoje.year
    fim_mes = ate_mes if ate_mes is not None else hoje.month

    # Do mais antigo para o mais recente
    periodos = [_mes_anterior(fim_ano, fim_mes, i) for i in range(meses - 1, -1, -1)]

    inicio = date(periodos[0][0], periodos[0][1], 1)
    prox_ano, prox_mes = _mes_anterior(fim_ano, fim_mes, -1)
    limite = date(prox_ano, prox_mes, 1)

    ano_col = extract("year", Pedido.data_pedido)
    mes_col = extract("month", Pedido.data_pedido)
    linhas = (
        session.query(
            ano_col,
            mes_col,
            func.count(func.distinct(Pedido.id)),
            func.coalesce(
                func.sum(ItemPedido.quantidade_total * ItemPedido.valor_unitario), 0
            ),
        )
        .select_from(Pedido)
        .outerjoin(ItemPedido, ItemPedido.pedido_id == Pedido.id)
        .filter(
            Pedido.status != STATUS_CANCELADO,
            Pedido.data_pedido >= inicio,
            Pedido.data_pedido < limite,
        )
        .group_by(ano_col, mes_col)
        .all()
    )
    por_periodo: Dict[Tuple[int, int], Tuple[int, float]] = {
        (int(a), int(m)): (int(qtd), float(valor or 0)) for a, m, qtd, valor in linhas
    }

    return {
        "meses": [
            {
                "ano": a,
                "mes": m,
                "quantidade_pedidos": por_periodo.get((a, m), (0, 0.0))[0],
                "valor_total": round(por_periodo.get((a, m), (0, 0.0))[1], 2),
            }
            for a, m in periodos
        ]
    }


# ---------------------------------------------------------
# GET /relatorios/ranking-clientes
# Clientes ativos com mais pedidos (não cancelados)
# ---------------------------------------------------------
@relatorios_router.get("/ranking-clientes")
def ranking_clientes(
    limite: int = Query(3, ge=1, le=50),
    session: Session = Depends(get_db),
):
    total = func.count(Pedido.id)
    linhas = (
        session.query(Cliente.id, Cliente.nome, total)
        .join(Pedido, Pedido.cliente_id == Cliente.id)
        .filter(Cliente.status.is_(True), Pedido.status != STATUS_CANCELADO)
        .group_by(Cliente.id, Cliente.nome)
        .order_by(total.desc(), Cliente.nome)
        .limit(limite)
        .all()
    )
    return {
        "clientes": [
            {"cliente_id": cid, "nome_cliente": nome, "quantidade_pedidos": qtd}
            for cid, nome, qtd in linhas
        ]
    }


# ---------------------------------------------------------
# GET /relatorios/pecas
# Peças dos pedidos, com agrupamento opcional
# ---------------------------------------------------------
@relatorios_router.get("/pecas")
def resumo_pecas(
    mes: Optional[int] = Query(None, ge=1, le=12),
    ano: Optional[int] = Query(None, ge=2000),
    agrupar_por: Optional[str] = Query(
        None, description="modelo, referencia, tecido, cor, tamanho ou cliente"
    ),
    session: Session = Depends(get_db),
):
    if agrupar_por is not None and agrupar_por not in AGRUPAMENTOS_PECAS:
        raise HTTPException(
            status_code=400,
            detail=f"agrupar_por deve ser um de: {', '.join(AGRUPAMENTOS_PECAS)}",
        )

    _, total_pecas, _ = _totais(session, mes, ano)

    resultados: List[dict] = []
    if agrupar_por is not None:
        itens = _filtro_periodo(
            session.query(ItemPedido)
            .join(Pedido, ItemPedido.pedido_id == Pedido.id)
            .filter(Pedido.status != STATUS_CANCELADO),
            mes,
            ano,
        ).all()

        pecas: Dict[str, int] = defaultdict(int)
        valor: Dict[str, float] = defaultdict(float)
        for item in itens:
            preco = float(item.valor_unitario or 0)
            if agrupar_por == "tamanho":
                grade = GRADE_LETRAS if len(item.quantidades) == len(GRADE_LETRAS) else GRADE_NUMEROS
                for tamanho, qtd in zip(grade, item.quantidades):
                    if qtd:
                        pecas[tamanho] += qtd
                        valor[tamanho] += qtd * preco
                continue
            if agrupar_por == "cliente":
                pedido = session.get(Pedido, item.pedido_id)
                chave = pedido.cliente.nome if pedido and pedido.cliente else "—"
            else:
                chave = getattr(item, agrupar_por)
            pecas[chave] += item.quantidade_total
            valor[chave] += item.quantidade_total * preco

        resultados = [
            {"grupo": chave, "total_pecas": pecas[chave], "valor_total": round(valor[chave], 2)}
            for chave in sorted(pecas, key=lambda k: (-pecas[k], k))
        ]

    return {
        "mes": mes,
        "ano": ano,
        "agrupar_por": agrupar_por,
        "total_pecas": total_pecas,
        "resultados": resultados,
    }


# ---------------------------------------------------------
# GET /relatorios/clientes/{id}
# Histórico de pedidos de um cliente
# ---------------------------------------------------------
@relatorios_router.get("/clientes/{id}")
def historico_cliente(id: int, session: Session = Depends(get_db)):
    cliente = session.get(Cliente, id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    pedidos = (
        session.query(Pedido)
        .filter(
            Pedido.cliente_id == id,
            Pedido.status != STATUS_CANCELADO,
        )
        .order_by(Pedido.id)
        .all()
    )
    saidas = [pedido_para_out(p) for p in pedidos]

    return {
        "cliente_id": id,
        "nome_cliente": cliente.nome,
        "quantidade_pedidos": len(saidas),
        "total_pecas": sum(p.total_pecas for p in saidas),
        "valor_acumulado": round(sum(p.valor_total for p in saidas), 2),
        "pedidos": saidas,
    }
