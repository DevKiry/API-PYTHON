from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from database import SessionLocal, engine

app = FastAPI(title="API de Confecção - Clientes")
models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def buscar_cliente_ou_404(db: Session, cliente_id: int) -> models.Cliente:
    cliente = db.get(models.Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


def documento_em_uso(db: Session, documento: Optional[str], ignorar_id: Optional[int] = None) -> bool:
    if not documento:
        return False
    consulta = db.query(models.Cliente).filter(models.Cliente.documento == documento)
    if ignorar_id is not None:
        consulta = consulta.filter(models.Cliente.id != ignorar_id)
    return db.query(consulta.exists()).scalar()


# POST /clientes — Cadastrar cliente
@app.post("/clientes", response_model=schemas.ClienteResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_cliente(dados: schemas.ClienteCreate, db: db_dependency):
    if documento_em_uso(db, dados.documento):
        raise HTTPException(status_code=409, detail="Já existe um cliente com esse documento")

    cliente = models.Cliente(**dados.model_dump(), status="ativo")
    db.add(cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um cliente com esse documento")
    db.refresh(cliente)
    return cliente


# GET /clientes — Listar clientes
@app.get("/clientes", response_model=schemas.ClienteListResponse)
def listar_clientes(
    db: db_dependency,
    busca: Optional[str] = Query(None, description="Pesquisa por nome ou telefone"),
    pagina: int = Query(1, ge=1, description="Página dos resultados"),
    limite: int = Query(20, ge=1, le=100, description="Quantidade de resultados por página"),
):
    consulta = db.query(models.Cliente)

    if busca:
        termo = f"%{busca}%"
        consulta = consulta.filter(
            or_(models.Cliente.nome.ilike(termo), models.Cliente.telefone.ilike(termo))
        )

    total = consulta.count()
    resultados = (
        consulta.order_by(models.Cliente.id)
        .offset((pagina - 1) * limite)
        .limit(limite)
        .all()
    )
    return {"total": total, "pagina": pagina, "limite": limite, "resultados": resultados}


# GET /clientes/{id} — Consultar cliente
@app.get("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def consultar_cliente(cliente_id: int, db: db_dependency):
    return buscar_cliente_ou_404(db, cliente_id)


# PUT /clientes/{id} — Editar cliente
@app.put("/clientes/{cliente_id}", response_model=schemas.ClienteResponse)
def editar_cliente(cliente_id: int, dados: schemas.ClienteUpdate, db: db_dependency):
    cliente = buscar_cliente_ou_404(db, cliente_id)

    if documento_em_uso(db, dados.documento, ignorar_id=cliente_id):
        raise HTTPException(status_code=409, detail="Já existe um cliente com esse documento")

    for campo, valor in dados.model_dump().items():
        setattr(cliente, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um cliente com esse documento")
    db.refresh(cliente)
    return cliente


# PATCH /clientes/{id}/status — Atualizar status do cliente (ativo | desativado)
@app.patch("/clientes/{cliente_id}/status", response_model=schemas.ClienteResponse)
def atualizar_status_cliente(cliente_id: int, dados: schemas.ClienteStatusUpdate, db: db_dependency):
    cliente = buscar_cliente_ou_404(db, cliente_id)
    cliente.status = dados.status
    db.commit()
    db.refresh(cliente)
    return cliente


# DELETE /clientes/{id} — Excluir cliente
@app.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cliente(cliente_id: int, db: db_dependency):
    cliente = buscar_cliente_ou_404(db, cliente_id)
    db.delete(cliente)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
