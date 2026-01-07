from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.base import SolicitacaoTFD, Paciente
from app.worker import processar_documento_task
import shutil
import os
import uuid

router = APIRouter()

@router.post("/processar-sus")
async def processar_documento_background(
    file: UploadFile = File(...),
    medico_id: str = Form(...),
    unidade_id: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Salvar arquivo temporariamente no disco
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{uuid.uuid4()}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Criar Paciente Provisório
    novo_paciente = Paciente(
        nome="Em Análise...", # Será atualizado pelo Worker
        cpf=f"TEMP-{uuid.uuid4().hex[:8]}",
        telefone=""
    )
    db.add(novo_paciente)
    db.commit()
    db.refresh(novo_paciente)

    # 3. Criar Solicitação "Pendente"
    nova_solicitacao = SolicitacaoTFD(
        paciente_id=novo_paciente.id,
        medico_solicitante_id=medico_id,
        unidade_solicitante_id=unidade_id,
        data_desejada=func.now(),
        status_pedido="Na_Fila_Processamento", # Status inicial
        procedimento="Analisando documento...",
        nivel_prioridade=0
    )
    db.add(nova_solicitacao)
    db.commit()
    db.refresh(nova_solicitacao)

    # 4. ENVIAR PARA A FILA (Isso libera o usuário imediatamente)
    processar_documento_task.delay(str(nova_solicitacao.id), file_path)

    return {
        "message": "Documento enviado para análise.",
        "status": "PROCESSANDO",
        "id_solicitacao": str(nova_solicitacao.id)
    }