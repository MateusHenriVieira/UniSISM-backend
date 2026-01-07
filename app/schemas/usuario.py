from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# O que recebemos ao criar um usuário
class UsuarioCreate(BaseModel):
    nome: str
    cpf: str
    perfil: str  # SUPER_ADMIN, GESTOR, MEDICO, MOTORISTA, etc.
    crm: Optional[str] = None
    
    # Lista de IDs das UBS onde ele trabalha (Opcional, só para médicos/recepção)
    unidades_ids: Optional[List[str]] = []

# O que recebemos ao atualizar
class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    perfil: Optional[str] = None
    crm: Optional[str] = None
    unidades_ids: Optional[List[str]] = None

# O que devolvemos para o Frontend (Sem senha!)
class UsuarioResponse(BaseModel):
    id: str
    nome: str
    cpf: str
    login: str
    perfil: str
    crm: Optional[str]
    primeiro_acesso: bool
    unidades: List[dict] = [] # Retorna nome e ID das unidades
    criado_em: datetime

    class Config:
        orm_mode = True