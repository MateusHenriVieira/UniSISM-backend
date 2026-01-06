from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ocr_service import OCRService
from app.db.base import Paciente, SolicitacaoTFD
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/processar-sus")
async def processar_documento_sus(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Motor OCR Inteligente:
    1. Lê CPF e Nome.
    2. Detecta Nível de Prioridade (Onco/Urgent/Eletivo).
    3. Atualiza cadastro se necessário.
    4. Gera o pré-cadastro da solicitação com a prioridade definida.
    """
    
    # 1. Leitura e Processamento via Serviço
    contents = await file.read()
    # O Service agora retorna 'cpf', 'nome' e 'prioridade'
    dados = OCRService.extrair_dados_sus(contents, file.filename)
    
    if not dados["cpf"]:
        raise HTTPException(status_code=400, detail="CPF não localizado no documento.")

    # 2. Gestão Inteligente do Paciente (Busca ou Cria)
    paciente = db.query(Paciente).filter(Paciente.cpf == dados["cpf"]).first()
    
    if not paciente:
        # Criação com UUID automático
        logger.info(f"Criando novo paciente via OCR: {dados['cpf']}")
        paciente = Paciente(
            cpf=dados["cpf"], 
            nome=dados["nome"]
        )
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
    else:
        # Lógica de Atualização Cadastral (Sua versão 'Mais Completa')
        # Se o nome gravado for genérico e o OCR achou um nome melhor agora, atualiza.
        if dados["nome"] != "Validar no Dashboard" and "Validar" in paciente.nome:
            logger.info(f"Atualizando nome do paciente {paciente.cpf} via OCR.")
            paciente.nome = dados["nome"]
            db.commit()
            db.refresh(paciente)

    # 3. Criação da Pré-Candidatura (Lógica BlaBlaCar)
    # Registramos a intenção e a PRIORIDADE detectada, mas o status fica 'Aguardando_Analise'
    # até o paciente ou gestor vincular a um ônibus específico.
    nova_solicitacao = SolicitacaoTFD(
        paciente_id=paciente.id,
        procedimento="Identificado via OCR (Aguardando vínculo com ônibus)",
        
        # AQUI ESTÁ O PULO DO GATO: Salvamos a prioridade médica extraída do PDF
        nivel_prioridade=dados.get("prioridade", 1),
        
        status_pedido="Aguardando_Analise", # Paciente ainda vai escolher a viagem
        tipo_transporte="Pendente",
        data_desejada=datetime.now() # Data base, será alterada quando escolher o ônibus
    )
    
    db.add(nova_solicitacao)
    db.commit()
    db.refresh(nova_solicitacao)

    # 4. Retorno Rico para o Frontend
    return {
        "status": "sucesso",
        "paciente": {
            "uuid": str(paciente.id),
            "nome": paciente.nome,
            "cpf": paciente.cpf
        },
        "analise_ia": {
            "prioridade_detectada": dados.get("prioridade", 1), # 1 a 5
            "motivo": "Termos médicos identificados no documento"
        },
        "solicitacao": {
            "id": str(nova_solicitacao.id),
            "status": nova_solicitacao.status_pedido
        },
        "mensagem": "Documento processado. Vá para o 'Mural de Viagens' para escolher seu ônibus."
    }