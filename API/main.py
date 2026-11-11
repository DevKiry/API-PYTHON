# API 1.0.0
# Autores: Caio, Gustavo e Joao

from contextlib import asynccontextmanager
from typing import AsyncIterator
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from cliente_route import clientes_router
from models import criar_tabelas
from pedido_route import pedidos_router
from relatorio_route import relatorios_router
 
 
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Cria as tabelas no banco ao iniciar a API."""
    criar_tabelas()
    yield
 
 
app = FastAPI(title="API", version="1.0.0", lifespan=lifespan)
 
# CORS: necessário para o app Flutter (web) conseguir chamar a API.
# Em produção, troque ["*"] pelo endereço real do app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(clientes_router)
app.include_router(pedidos_router)
app.include_router(relatorios_router)

# Para rodar o nosso codigo, executar no terminal: uvicorn main:app --reload