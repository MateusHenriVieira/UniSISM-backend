from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.session import get_db
from app.db.base import Paciente, SolicitacaoTFD, CronogramaViagem
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
import uuid

router = APIRouter()

# --- Schemas ---
class CronogramaCreate(BaseModel):
    destino: str
    data_hora_saida: datetime
    placa: str
    motorista: str
    capacidade: int = 40

class CandidaturaVaga(BaseModel):
    cpf_paciente: str
    id_viagem: str  # UUID do ônibus escolhido no "BlaBlaCar"
    prioridade_ocr: int = 1 # Vem do retorno do OCR
    com_acompanhante: bool = False
    procedimento: str

# ==========================================
# 1. Gestão de Frota (Cadastro de Viagens)
# ==========================================
@router.post("/cronograma/criar")
async def criar_viagem(dados: CronogramaCreate, db: Session = Depends(get_db)):
    nova_viagem = CronogramaViagem(
        data_partida=dados.data_hora_saida,
        destino=dados.destino,
        placa=dados.placa,
        motorista=dados.motorista,
        capacidade_total=dados.capacidade
    )
    db.add(nova_viagem)
    db.commit()
    return {"msg": "Viagem criada no mural.", "id": str(nova_viagem.id)}

# ==========================================
# 2. BlaBlaCar do Paciente (Mural e Candidatura)
# ==========================================

@router.get("/mural-viagens")
async def buscar_viagens(destino: Optional[str] = None, data: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Retorna as viagens disponíveis (Estilo busca do BlaBlaCar).
    Mostra: Horário, Motorista, Vagas Restantes.
    """
    query = db.query(CronogramaViagem).filter(CronogramaViagem.data_partida >= datetime.now())
    
    if destino:
        query = query.filter(CronogramaViagem.destino.ilike(f"%{destino}%"))
    if data:
        # Filtra pelo dia (ignorando hora)
        data_obj = datetime.strptime(data, "%Y-%m-%d").date()
        query = query.filter(func.date(CronogramaViagem.data_partida) == data_obj)

    viagens = query.order_by(CronogramaViagem.data_partida).all()
    
    # Formata retorno visual para o App
    resultado = []
    for v in viagens:
        vagas_livres = v.capacidade_total - v.vagas_ocupadas
        resultado.append({
            "id_viagem": str(v.id),
            "origem": "Águas Belas",
            "destino": v.destino,
            "data_hora": v.data_partida,
            "motorista": v.motorista,
            "veiculo": v.placa,
            "vagas_disponiveis": vagas_livres,
            "status_lotacao": "Lotado" if vagas_livres <= 0 else "Disponível"
        })
    return resultado

@router.post("/candidatar-vaga")
async def solicitar_vaga_blablacar(candidatura: CandidaturaVaga, db: Session = Depends(get_db)):
    """
    Paciente clica em 'Solicitar' no ônibus.
    NÃO reserva a vaga imediatamente. Entra na fila para análise do gestor.
    """
    paciente = db.query(Paciente).filter(Paciente.cpf == candidatura.cpf_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    # Verifica se a viagem existe
    viagem = db.query(CronogramaViagem).filter(CronogramaViagem.id == candidatura.id_viagem).first()
    if not viagem:
        raise HTTPException(status_code=404, detail="Viagem não encontrada.")

    # Cria a "Intenção de Viagem"
    solicitacao = SolicitacaoTFD(
        paciente_id=paciente.id,
        viagem_id=viagem.id,
        data_desejada=viagem.data_partida,
        com_acompanhante=candidatura.com_acompanhante,
        nivel_prioridade=candidatura.prioridade_ocr, # Define a ordem na fila
        procedimento=candidatura.procedimento,
        status_pedido="Aguardando_Analise",
        tipo_transporte="Onibus"
    )
    
    db.add(solicitacao)
    db.commit()
    
    return {
        "status": "Candidatura Registrada",
        "mensagem": "Sua solicitação foi enviada para o gestor. Você será notificado se a vaga for confirmada.",
        "prioridade_considerada": candidatura.prioridade_ocr
    }

# ==========================================
# 3. Visão do Gestor (Aprovação por Prioridade)
# ==========================================

@router.get("/gestao/candidatos/{id_viagem}")
async def listar_candidatos_viagem(id_viagem: str, db: Session = Depends(get_db)):
    """
    Mostra quem quer ir nesse ônibus, ORDENADO POR PRIORIDADE (5 primeiro).
    Isso ajuda o gestor a decidir quem viaja.
    """
    candidatos = db.query(SolicitacaoTFD, Paciente).join(Paciente).filter(
        SolicitacaoTFD.viagem_id == id_viagem,
        SolicitacaoTFD.status_pedido == "Aguardando_Analise"
    ).order_by(
        desc(SolicitacaoTFD.nivel_prioridade), # Prioridade maior no topo
        SolicitacaoTFD.criado_em               # Quem pediu primeiro como desempate
    ).all()
    
    lista = []
    for sol, pac in candidatos:
        vagas_req = 2 if sol.com_acompanhante else 1
        lista.append({
            "id_solicitacao": str(sol.id),
            "paciente": pac.nome,
            "cpf": pac.cpf,
            "prioridade": sol.nivel_prioridade, # Ex: 5 (Onco)
            "procedimento": sol.procedimento,
            "vagas_solicitadas": vagas_req,
            "acompanhante": "Sim" if sol.com_acompanhante else "Não"
        })
    return lista

@router.post("/gestao/aprovar/{id_solicitacao}")
async def aprovar_candidato(id_solicitacao: str, db: Session = Depends(get_db)):
    """
    O Gestor clica em 'Aprovar'.
    SÓ AGORA a vaga do ônibus é consumida.
    """
    solicitacao = db.query(SolicitacaoTFD).filter(SolicitacaoTFD.id == id_solicitacao).first()
    if not solicitacao: raise HTTPException(404, detail="Solicitação não encontrada.")
    
    viagem = db.query(CronogramaViagem).filter(CronogramaViagem.id == solicitacao.viagem_id).first()
    
    # Verifica capacidade REAL no momento do clique
    vagas_necessarias = 2 if solicitacao.com_acompanhante else 1
    if (viagem.capacidade_total - viagem.vagas_ocupadas) < vagas_necessarias:
        raise HTTPException(400, detail="Não há mais vagas neste ônibus. Rejeite ou encaminhe para Ajuda de Custo.")

    # Efetiva a reserva
    viagem.vagas_ocupadas += vagas_necessarias
    solicitacao.status_pedido = "Aprovado_Onibus"
    solicitacao.status_aprovacao = True
    
    db.commit()
    
    return {"status": "Confirmado", "msg": f"Paciente {solicitacao.paciente_id} confirmado no ônibus. Vagas restantes: {viagem.capacidade_total - viagem.vagas_ocupadas}"}