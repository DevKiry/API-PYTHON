from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Status definidos pelo grupo
StatusCliente = Literal["ativo", "desativado"]


class ClienteBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    telefone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=150)
    documento: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = Field(None, max_length=255)


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class ClienteStatusUpdate(BaseModel):
    status: StatusCliente


class ClienteResponse(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusCliente


class ClienteListResponse(BaseModel):
    total: int
    pagina: int
    limite: int
    resultados: List[ClienteResponse]
