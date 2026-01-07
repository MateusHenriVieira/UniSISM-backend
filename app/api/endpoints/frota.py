from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.base import CronogramaViagem, SolicitacaoTFD, Paciente, Usuario
from app.api.deps import ChecarPermissao, get_usuario_atual
from pydantic import BaseModel
from datetime import datetime
from typing import List

router = APIRouter()

# --- Schemas (Modelos de Dados) ---
class ViagemCreate(BaseModel):
    destino: str
    data_partida: datetime
    placa: str
    motorista_nome: str # Nome exato do motorista cadastrado no sistema
    capacidade: int

class PassageiroEmbarque(BaseModel):
    id_solicitacao: str
    nome_paciente: str
    rg_cpf: str
    acompanhante: bool
    status_embarque: str # PENDENTE, EMBARCOU, AUSENTE
    local_origem: str # UBS de onde veio

# ==========================================
# 1. Área do GESTOR (Criar Viagens)
# ==========================================
@router.post("/viagens", dependencies=[Depends(ChecarPermissao(["GESTOR", "SUPER_ADMIN"]))])
async def criar_viagem(dados: ViagemCreate, db: Session = Depends(get_db)):
    nova_viagem = CronogramaViagem(
        destino=dados.destino,
        data_partida=dados.data_partida,
        placa=dados.placa,
        motorista=dados.motorista_nome, # Vincula pelo nome
        capacidade_total=dados.capacidade
    )
    db.add(nova_viagem)
    db.commit()
    return {"msg": "Viagem criada com sucesso", "id": str(nova_viagem.id)}

@router.get("/viagens", dependencies=[Depends(ChecarPermissao(["GESTOR", "SUPER_ADMIN", "SECRETARIO"]))])
async def listar_todas_viagens(db: Session = Depends(get_db)):
    return db.query(CronogramaViagem).order_by(CronogramaViagem.data_partida.desc()).all()

# ==========================================
# 2. Área do MOTORISTA (App Mobile)
# ==========================================

@router.get("/motorista/meus-trajetos", dependencies=[Depends(ChecarPermissao(["MOTORISTA", "SUPER_ADMIN"]))])
async def minhas_viagens_hoje(
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db)
):
    """
    Lista apenas as viagens atribuídas a este motorista.
    Filtra pelo NOME do usuário logado.
    """
    # Busca viagens futuras ou do dia
    viagens = db.query(CronogramaViagem).filter(
        CronogramaViagem.motorista == usuario.nome,
        CronogramaViagem.data_partida >= datetime.now().replace(hour=0, minute=0, second=0)
    ).order_by(CronogramaViagem.data_partida).all()
    
    return [
        {
            "id": str(v.id),
            "destino": v.destino,
            "data": v.data_partida,
            "placa": v.placa,
            "lotacao": f"{v.vagas_ocupadas}/{v.capacidade_total}"
        } 
        for v in viagens
    ]

@router.get("/motorista/embarque/{viagem_id}", response_model=List[PassageiroEmbarque], dependencies=[Depends(ChecarPermissao(["MOTORISTA", "SUPER_ADMIN"]))])
async def lista_passageiros(viagem_id: str, db: Session = Depends(get_db)):
    """
    Retorna a 'Prancheta Digital': Lista de passageiros APROVADOS para aquela viagem.
    """
    solicitacoes = db.query(SolicitacaoTFD).filter(
        SolicitacaoTFD.viagem_id == viagem_id,
        SolicitacaoTFD.status_pedido == "Aprovado_Onibus" # Só mostra quem foi aprovado pelo Gestor
    ).all()
    
    resultado = []
    for sol in solicitacoes:
        paciente = db.query(Paciente).filter(Paciente.id == sol.paciente_id).first()
        
        # Busca nome da UBS de origem para o motorista saber onde pegar (opcional)
        origem = "Não informada"
        if sol.unidade_solicitante_id:
            # Aqui poderia fazer uma query para pegar o nome da UBS
            origem = "UBS Vinculada" 

        resultado.append({
            "id_solicitacao": str(sol.id),
            "nome_paciente": paciente.nome,
            "rg_cpf": paciente.cpf,
            "acompanhante": sol.com_acompanhante,
            "status_embarque": sol.status_embarque, # O motorista vê se já marcou
            "local_origem": origem
        })
    
    return resultado

@router.put("/motorista/confirmar-presenca/{solicitacao_id}", dependencies=[Depends(ChecarPermissao(["MOTORISTA", "SUPER_ADMIN"]))])
async def realizar_checkin(
    solicitacao_id: str, 
    status: str, # Deve enviar "EMBARCOU" ou "AUSENTE"
    db: Session = Depends(get_db)
):
    """
    O Motorista clica no botão 'Check-in' ou 'Faltou'.
    """
    if status not in ["EMBARCOU", "AUSENTE", "PENDENTE"]:
        raise HTTPException(400, "Status inválido")

    solicitacao = db.query(SolicitacaoTFD).filter(SolicitacaoTFD.id == solicitacao_id).first()
    if not solicitacao:
        raise HTTPException(404, "Solicitação não encontrada")
    
    solicitacao.status_embarque = status
    db.commit()
    
    msg = "Embarque confirmado!" if status == "EMBARCOU" else "Paciente marcado como ausente."
    return {"message": msg, "novo_status": status}