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
    Motor OCR Híbrido:
    - Reconhece se é 'Laudo Médico' (Gera Demanda + Prioridade) 
    - Reconhece se é 'Comprovante de Agendamento' (Gera Logística + Data)
    """
    
    # 1. Leitura e Classificação do Documento
    contents = await file.read()
    # Retorna dicionário com 'tipo_doc', 'cid', 'prioridade', 'data_exame', etc.
    dados = OCRService.extrair_dados_sus(contents, file.filename)
    
    if not dados["cpf"]:
        raise HTTPException(status_code=400, detail="CPF não localizado. Verifique a qualidade da imagem.")

    # 2. Gestão Inteligente do Paciente
    paciente = db.query(Paciente).filter(Paciente.cpf == dados["cpf"]).first()
    
    if not paciente:
        logger.info(f"Cadastro automático via OCR: {dados['cpf']}")
        paciente = Paciente(
            cpf=dados["cpf"], 
            nome=dados["nome"],
            telefone=dados.get("telefone") # Captura telefone do laudo ou comprovante
        )
        db.add(paciente)
        db.commit()
        db.refresh(paciente)
    else:
        # Atualização Cadastral Incrementals
        mudou = False
        if dados["nome"] != "Validar no Dashboard" and "Validar" in paciente.nome:
            paciente.nome = dados["nome"]
            mudou = True
        
        # Se o paciente não tinha telefone e o documento trouxe um, atualiza
        if dados.get("telefone") and not paciente.telefone:
            paciente.telefone = dados["telefone"]
            mudou = True
            
        if mudou:
            db.commit()
            db.refresh(paciente)

    # 3. Definição da Data da Viagem
    # - Se for COMPROVANTE: Usamos a data exata do exame.
    # - Se for LAUDO: Usamos a data de hoje como 'Data de Solicitação' (pois a viagem ainda não existe).
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
            logger.warning(f"Data ilegível no OCR: {dados['data_exame']}")
            # Mantém data atual se falhar

    # 4. Enriquecimento da Descrição do Procedimento
    # Se for Laudo com CID, adicionamos essa info visualmente
    descricao_procedimento = dados["procedimento"] or "Identificado via OCR"
    if dados.get("cid"):
        descricao_procedimento += f" (CID Detectado: {dados['cid']})"

    # 5. Criação da Solicitação
    nova_solicitacao = SolicitacaoTFD(
        paciente_id=paciente.id,
        procedimento=descricao_procedimento,
        
        # AQUI O OCR BRILHA: Define se é Prioridade 5 (Onco) ou 1 (Rotina)
        nivel_prioridade=dados.get("prioridade", 1),
        
        # Data extraída do comprovante OU data de hoje (para laudos)
        data_desejada=data_referencia,
        
        # Status inicial
        status_pedido="Aguardando_Analise", 
        tipo_transporte="Pendente"
    )
    
    db.add(nova_solicitacao)
    db.commit()
    db.refresh(nova_solicitacao)

    # 6. Retorno Contextualizado
    mensagem_retorno = "Documento processado."
    if dados["tipo_doc"] == "LAUDO_SOLICITACAO":
        mensagem_retorno = f"Laudo Médico identificado. Prioridade Nível {dados['prioridade']} atribuída devido ao diagnóstico."
    elif dados["tipo_doc"] == "COMPROVANTE_AGENDAMENTO":
        mensagem_retorno = f"Agendamento confirmado para {dados.get('destino_detectado', 'destino externo')}. Data da viagem pré-preenchida."

    return {
        "status": "sucesso",
        "tipo_documento_detectado": dados["tipo_doc"], # Útil para o frontend mostrar ícone diferente
        "paciente": {
            "uuid": str(paciente.id),
            "nome": paciente.nome,
            "cpf": paciente.cpf,
            "telefone": paciente.telefone
        },
        "analise_ia": {
            "prioridade": dados.get("prioridade", 1),
            "cid_suspeito": dados.get("cid"),
            "destino_sugerido": dados.get("destino_detectado"),
            "data_leitura": dados.get("data_exame")
        },
        "solicitacao": {
            "id": str(nova_solicitacao.id),
            "procedimento": nova_solicitacao.procedimento,
            "data_considerada": nova_solicitacao.data_desejada
        },
        "mensagem": mensagem_retorno
    }