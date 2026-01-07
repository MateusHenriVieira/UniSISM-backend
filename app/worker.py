from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.base import SolicitacaoTFD, Paciente
from app.services.ocr_service import OCRService # <--- Importação Corrigida
import os

@celery_app.task(name="processar_documento_task")
def processar_documento_task(solicitacao_id: str, file_path: str):
    """
    Worker que roda em background.
    Agora usa a classe OCRService robusta.
    """
    db = SessionLocal()
    solicitacao = db.query(SolicitacaoTFD).filter(SolicitacaoTFD.id == solicitacao_id).first()
    
    if not solicitacao:
        return "Solicitação não encontrada"

    try:
        # 1. Atualiza status para Processando
        solicitacao.status_pedido = "Processando_IA"
        db.commit()

        # 2. Ler o arquivo do disco para passar para o Serviço
        if not os.path.exists(file_path):
            raise FileNotFoundError("Arquivo temporário sumiu antes do processamento.")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        # 3. CHAMA O NOVO SERVIÇO ENTERPRISE
        # Extrai o nome do arquivo para saber se é PDF ou JPG
        filename = os.path.basename(file_path)
        
        # A mágica acontece aqui:
        resultado = OCRService.extrair_dados_sus(file_bytes, filename)
        
        # 4. Atualiza o Banco com o Resultado
        # Mapeia os dados retornados pelo serviço para o banco
        if resultado.get("prioridade"):
            solicitacao.nivel_prioridade = resultado["prioridade"]
        
        if resultado.get("procedimento"):
            solicitacao.procedimento = resultado["procedimento"]
            
        solicitacao.status_pedido = "Aguardando_Analise" # Libera para o Gestor

        # Atualiza dados do Paciente se a IA achou algo melhor
        paciente = db.query(Paciente).filter(Paciente.id == solicitacao.paciente_id).first()
        if paciente:
            if resultado.get("nome") and resultado["nome"] != "Validar no Dashboard":
                paciente.nome = resultado["nome"]
            if resultado.get("cpf"):
                paciente.cpf = resultado["cpf"]
            if resultado.get("telefone"):
                paciente.telefone = resultado["telefone"]

        db.commit()
        
        # Limpeza: Remove o arquivo temporário para não encher o disco
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return f"Sucesso: {resultado['tipo_doc']} processado."

    except Exception as e:
        print(f"Erro no Worker: {e}")
        solicitacao.status_pedido = "Erro_OCR"
        solicitacao.procedimento = f"Falha na leitura: {str(e)[:100]}"
        db.commit()
        return f"Erro fatal: {str(e)}"
    finally:
        db.close()