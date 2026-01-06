from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.db.base import Usuario, UnidadeSaude, SolicitacaoTFD
from pydantic import BaseModel
from typing import List
import uuid

router = APIRouter()

# --- Schemas ---
class SelecaoUnidade(BaseModel):
    medico_id: str
    unidade_id: str

# 1. Login/Seleção de Contexto
@router.get("/meus-postos/{medico_id}")
async def listar_postos_do_medico(medico_id: str, db: Session = Depends(get_db)):
    """
    No login, o médico vê: 'Olá Dr. Fernando, onde você está atendendo hoje?'
    Retorna lista: [UBS Vila Ferreira, UBS Centro...]
    """
    medico = db.query(Usuario).filter(Usuario.id == medico_id).first()
    if not medico: raise HTTPException(404, detail="Médico não encontrado")
    
    return [
        {"id": str(u.id), "nome": u.nome, "bairro": u.bairro} 
        for u in medico.unidades
    ]

# 2. Dashboard de Produção do Médico
@router.get("/dashboard-producao")
async def dashboard_producao(
    medico_id: str, 
    unidade_id: str, 
    db: Session = Depends(get_db)
):
    """
    Painel de Controle: Mostra o que o médico produziu NAQUELA unidade específica.
    """
    # Total de solicitações feitas por este médico nesta unidade
    total_solicitacoes = db.query(func.count(SolicitacaoTFD.id)).filter(
        SolicitacaoTFD.medico_solicitante_id == medico_id,
        SolicitacaoTFD.unidade_solicitante_id == unidade_id
    ).scalar()

    # Pacientes com Alta Prioridade (Oncologia/Urgente)
    alta_prioridade = db.query(func.count(SolicitacaoTFD.id)).filter(
        SolicitacaoTFD.medico_solicitante_id == medico_id,
        SolicitacaoTFD.unidade_solicitante_id == unidade_id,
        SolicitacaoTFD.nivel_prioridade >= 4
    ).scalar()

    # Status dos Pedidos (Para ele acompanhar se conseguiu a vaga)
    aprovados = db.query(func.count(SolicitacaoTFD.id)).filter(
        SolicitacaoTFD.medico_solicitante_id == medico_id,
        SolicitacaoTFD.unidade_solicitante_id == unidade_id,
        SolicitacaoTFD.status_pedido == "Aprovado_Onibus"
    ).scalar()

    return {
        "unidade_atual": unidade_id,
        "producao_geral": {
            "total_encaminhamentos": total_solicitacoes,
            "casos_graves": alta_prioridade,
            "viagens_confirmadas": aprovados,
            "pendentes": total_solicitacoes - aprovados
        }
    }