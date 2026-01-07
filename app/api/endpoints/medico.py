from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.db.base import Usuario, SolicitacaoTFD, Paciente, UnidadeSaude
from app.api.deps import get_usuario_atual, ChecarPermissao

router = APIRouter()

# --- Schemas de Resposta ---
class DashboardStats(BaseModel):
    total_encaminhados: int
    aprovados: int
    aguardando: int
    pacientes_totais: int

class EncaminhamentoDetalhe(BaseModel):
    id: str
    paciente_nome: str
    cpf: str
    procedimento: str
    prioridade: int
    status: str
    data_solicitacao: datetime
    unidade_destino: Optional[str] = "Regulação Central"

class PerfilUpdate(BaseModel):
    nome: Optional[str] = None
    nova_senha: Optional[str] = None
    avatar_url: Optional[str] = None # Futuro: Upload de imagem

# --- Rotas ---

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    unidade_id: str, # O frontend envia qual unidade o médico está operando
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    """Retorna os cards estatísticos da UBS"""
    # Filtra solicitações desta unidade
    query_base = db.query(SolicitacaoTFD).filter(SolicitacaoTFD.unidade_solicitante_id == unidade_id)
    
    total = query_base.count()
    aprovados = query_base.filter(SolicitacaoTFD.status_pedido.ilike("%Aprovado%")).count()
    aguardando = query_base.filter(SolicitacaoTFD.status_pedido == "Aguardando_Analise").count()
    
    # Pacientes únicos atendidos nesta unidade (Exemplo simplificado)
    # Em produção real, você teria uma tabela de vínculo Paciente <-> Unidade
    pacientes_ids = db.query(SolicitacaoTFD.paciente_id).filter(SolicitacaoTFD.unidade_solicitante_id == unidade_id).distinct().count()

    return {
        "total_encaminhados": total,
        "aprovados": aprovados,
        "aguardando": aguardando,
        "pacientes_totais": pacientes_ids
    }

@router.get("/encaminhamentos", response_model=List[EncaminhamentoDetalhe])
async def listar_encaminhamentos_ubs(
    unidade_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    """Lista todos os encaminhamentos feitos por esta UBS"""
    solicitacoes = db.query(SolicitacaoTFD).filter(
        SolicitacaoTFD.unidade_solicitante_id == unidade_id
    ).order_by(SolicitacaoTFD.criado_em.desc()).all()

    resultado = []
    for sol in solicitacoes:
        paciente = db.query(Paciente).filter(Paciente.id == sol.paciente_id).first()
        resultado.append({
            "id": str(sol.id),
            "paciente_nome": paciente.nome if paciente else "Desconhecido",
            "cpf": paciente.cpf if paciente else "---",
            "procedimento": sol.procedimento,
            "prioridade": sol.nivel_prioridade,
            "status": sol.status_pedido,
            "data_solicitacao": sol.criado_em
        })
    return resultado

@router.put("/perfil/me")
async def atualizar_perfil(
    dados: PerfilUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual)
):
    """Atualiza dados básicos do usuário logado"""
    if dados.nome:
        usuario.nome = dados.nome
    
    if dados.nova_senha:
        from app.core.security import criar_hash_senha
        usuario.senha_hash = criar_hash_senha(dados.nova_senha)
    
    db.commit()
    return {"message": "Perfil atualizado com sucesso!"}