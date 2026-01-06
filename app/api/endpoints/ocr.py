from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.ocr_service import OCRService
from app.db.base import Paciente, SolicitacaoTFD
from datetime import datetime
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/processar-sus")
async def processar_documento_sus(
    file: UploadFile = File(...), 
    medico_id: str = Form(...),    # <--- NOVO: ID do Médico (vido do login)
    unidade_id: str = Form(...),   # <--- NOVO: ID da UBS (selecionada no login)
    db: Session = Depends(get_db)
):
    """
    Motor OCR Híbrido & Rastreável:
    1. Recebe o PDF + Contexto (Quem enviou e de qual Posto).
    2. Classifica: 'Laudo Médico' (Prioridade) ou 'Comprovante' (Logística).
    3. Vincula o paciente ao Posto de Origem.
    4. Cria a solicitação ligada ao Médico Solicitante.
    """
    
    # 1. Leitura e Classificação via Serviço
    contents = await file.read()
    dados = OCRService.extrair_dados_sus(contents, file.filename)
    
    if not dados["cpf"]:
        raise HTTPException(status_code=400, detail="CPF não localizado. Verifique a qualidade da imagem.")

    # 2. Gestão Inteligente do Paciente
    paciente = db.query(Paciente).filter(Paciente.cpf == dados["cpf"]).first()
    
    if not paciente:
        logger.info(f"Cadastro automático via OCR no posto {unidade_id}: {dados['cpf']}")
        paciente = Paciente(
            cpf=dados["cpf"], 
            nome=dados["nome"],
            telefone=dados.get("telefone"),
            unidade_origem_id=unidade_id # <--- Vincula o paciente a esta UBS
        )
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
    else:
        # Atualização Cadastral Incremental
        mudou = False
        if dados["nome"] != "Validar no Dashboard" and "Validar" in paciente.nome:
            paciente.nome = dados["nome"]
            mudou = True
        
        if dados.get("telefone") and not paciente.telefone:
            paciente.telefone = dados["telefone"]
            mudou = True
        
        # Se o paciente ainda não tinha "casa", define esta UBS como origem
        if not paciente.unidade_origem_id:
            paciente.unidade_origem_id = unidade_id
            mudou = True

        if mudou:
            db.commit()
            db.refresh(paciente)

    # 3. Tratamento da Data (Híbrido)
    data_referencia = datetime.now()
    if dados.get("data_exame"):
        try:
            data_str = dados["data_exame"]
            if dados.get("hora_exame"):
                data_str += f" {dados['hora_exame']}"
                data_referencia = datetime.strptime(data_str, "%d/%m/%Y %H:%M")
            else:
                data_referencia = datetime.strptime(data_str, "%d/%m/%Y")
        except ValueError:
            logger.warning(f"Data ilegível: {dados['data_exame']}")

    # 4. Descrição Rica
    descricao_procedimento = dados["procedimento"] or "Identificado via OCR"
    if dados.get("cid"):
        descricao_procedimento += f" (CID: {dados['cid']})"

    # 5. Criação da Solicitação com RASTREABILIDADE
    nova_solicitacao = SolicitacaoTFD(
        paciente_id=paciente.id,
        
        # RASTREABILIDADE (O Pulo do Gato)
        unidade_solicitante_id=unidade_id,
        medico_solicitante_id=medico_id,
        
        procedimento=descricao_procedimento,
        nivel_prioridade=dados.get("prioridade", 1),
        data_desejada=data_referencia,
        status_pedido="Aguardando_Analise", 
        tipo_transporte="Pendente"
    )
    
    db.add(nova_solicitacao)
    db.commit()
    db.refresh(nova_solicitacao)

    # 6. Retorno Rico
    msg = "Documento processado."
    if dados["tipo_doc"] == "LAUDO_SOLICITACAO":
        msg = f"Laudo de {dados.get('prioridade')}ª prioridade recebido da unidade."
    elif dados["tipo_doc"] == "COMPROVANTE_AGENDAMENTO":
        msg = f"Retorno de agendamento processado para {dados.get('destino_detectado')}."

    return {
        "status": "sucesso",
        "rastreabilidade": {
            "unidade_id": unidade_id,
            "medico_id": medico_id
        },
        "tipo_documento": dados["tipo_doc"],
        "paciente": {
            "uuid": str(paciente.id),
            "nome": paciente.nome,
            "cpf": paciente.cpf
        },
        "analise_ia": {
            "prioridade": dados.get("prioridade", 1),
            "cid": dados.get("cid"),
            "destino": dados.get("destino_detectado")
        },
        "solicitacao": {
            "id": str(nova_solicitacao.id),
            "status": nova_solicitacao.status_pedido
        },
        "mensagem": msg
    }