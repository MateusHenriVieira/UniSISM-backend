import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import re
import io
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

class OCRService:
    @staticmethod
    def extrair_dados_sus(file_bytes: bytes, filename: str) -> dict:
        """
        Extrai dados de documentos SUS (PDF ou Imagem) utilizando OCR.
        Identifica automaticamente o tipo de documento e aplica a lógica de extração correspondente.
        """
        text = ""
        
        try:
            # 1. Conversão PDF/Imagem para Texto
            if filename.lower().endswith(".pdf"):
                try:
                    images = convert_from_bytes(file_bytes)
                    for img in images:
                        text += pytesseract.image_to_string(img, lang='por')
                except Exception as e:
                     logger.error(f"Erro ao converter PDF: {e}")
                     raise ValueError("Falha ao processar arquivo PDF. Verifique se é um PDF válido.")

            else:
                try:
                    image = Image.open(io.BytesIO(file_bytes))
                    text = pytesseract.image_to_string(image, lang='por')
                except Exception as e:
                    logger.error(f"Erro ao processar imagem: {e}")
                    raise ValueError("Falha ao processar imagem. Formato não suportado ou arquivo corrompido.")
            
            text_upper = text.upper()
            
            # 2. Roteamento Inteligente: Identificação do Tipo de Documento
            if "COMPROVANTE DE AGENDAMENTO" in text_upper:
                logger.info("OCR detectou: Comprovante de Agendamento (Volta do SUS)")
                return OCRService._processar_comprovante_agendamento(text, text_upper)
            
            elif "LAUDO PARA SOLICITAÇÃO" in text_upper or "PROCEDIMENTO AMBULATORIAL" in text_upper:
                logger.info("OCR detectou: Laudo Médico (Pedido do Doutor)")
                return OCRService._processar_laudo_medico(text, text_upper)
            
            else:
                # Tenta um processamento genérico se não reconhecer o cabeçalho específico
                logger.warning("Tipo de documento não reconhecido automaticamente. Tentando extração genérica.")
                return OCRService._processar_generico(text, text_upper)

        except Exception as e:
            logger.exception("Erro fatal no serviço de OCR.")
            # Retorna estrutura de erro para não quebrar a API
            return {
                "tipo_doc": "ERRO",
                "prioridade": 0,
                "erro": str(e)
            }

    # --- Lógica 1: Comprovante de Agendamento (Retorno do SUS) ---
    @staticmethod
    def _processar_comprovante_agendamento(text: str, text_upper: str) -> dict:
        dados = {
            "tipo_doc": "COMPROVANTE_AGENDAMENTO",
            "cpf": None,
            "nome": "Validar no Dashboard",
            "data_exame": None,
            "hora_exame": None,
            "procedimento": None,
            "destino_detectado": None,
            "prioridade": 1,
            "telefone": None
        }

        # Extração de CPF
        cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        if cpf_match: dados["cpf"] = cpf_match.group(0)

        # Extração de Nome
        nome_match = re.search(r'NOME:\s*(.*)', text_upper)
        if nome_match: 
            # Tenta limpar o texto capturado para pegar apenas o nome antes do telefone
            dados["nome"] = nome_match.group(1).split("TELEFONE")[0].strip()

        # Extração de Data
        data_match = re.search(r'DATA:\s*(\d{2}/\d{2}/\d{4})', text_upper)
        if data_match: dados["data_exame"] = data_match.group(1)

        # Extração de Hora
        hora_match = re.search(r'HORA:\s*(\d{2}:\d{2})', text_upper)
        if hora_match: dados["hora_exame"] = hora_match.group(1)
        
        # Detecção de Destino
        if "GARANHUNS" in text_upper: dados["destino_detectado"] = "GARANHUNS"
        elif "RECIFE" in text_upper: dados["destino_detectado"] = "RECIFE"

        # Prioridade baseada no procedimento agendado
        proc_match = re.search(r'ITEM AGENDAMENTO:\s*(.*)', text_upper)
        if proc_match: 
            dados["procedimento"] = proc_match.group(1).strip()
            # Se já está agendado e é oncológico, prioridade máxima
            if "ONCOLOGIA" in dados["procedimento"]: dados["prioridade"] = 5
        
        return dados

    # --- Lógica 2: Laudo Médico (Solicitação Inicial) ---
    @staticmethod
    def _processar_laudo_medico(text: str, text_upper: str) -> dict:
        dados = {
            "tipo_doc": "LAUDO_SOLICITACAO", 
            "cpf": None,
            "nome": "Validar no Dashboard",
            "data_exame": None, # Laudo não tem data de viagem ainda
            "procedimento": None,
            "prioridade": 1,
            "telefone": None,
            "cid": None
        }

        # 1. CPF (Busca em todo o texto)
        cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        if cpf_match: dados["cpf"] = cpf_match.group(0)

        # 2. Nome (Geralmente abaixo de "Nome do cidadão")
        linhas = text.split('\n')
        for i, linha in enumerate(linhas):
            if "Nome do cidadão" in linha:
                if i + 1 < len(linhas):
                    # Tenta pegar a próxima linha não vazia
                    proxima_linha = linhas[i+1].strip()
                    if proxima_linha:
                        dados["nome"] = proxima_linha
                    elif i + 2 < len(linhas):
                         dados["nome"] = linhas[i+2].strip()
                break
        
        # 3. Telefone
        tel_match = re.search(r'Telefone\s*([\(\)0-9\-\s]+)', text)
        if tel_match: dados["telefone"] = tel_match.group(1).strip()

        # 4. Procedimento Solicitado
        for i, linha in enumerate(linhas):
            if "PROCEDIMENTO SOLICITADO" in linha.upper():
                if i + 1 < len(linhas):
                    dados["procedimento"] = linhas[i+1].strip()
                break

        # 5. ANÁLISE DE RISCO (CID10 e Justificativa)
        # Captura o CID (Ex: C61)
        cid_match = re.search(r'CID10\s*([A-Z]\d{2,3}|.*)', text_upper)
        if cid_match:
            dados["cid"] = cid_match.group(1).split("-")[0].strip()

        # Regras de Prioridade para o Laudo
        texto_analise = text_upper
        
        # Prioridade 5: Câncer (CID C*), Neoplasia Maligna, Hemodiálise
        if dados["cid"] and dados["cid"].startswith("C"):
            dados["prioridade"] = 5
        elif any(t in texto_analise for t in ["NEOPLASIA MALIGNA", "CANCER", "ONCOLOGIA", "HEMODIALISE"]):
            dados["prioridade"] = 5
        
        # Prioridade 3: Urgente, Risco
        elif any(t in texto_analise for t in ["URGENTE", "PRIORIDADE", "RISCO"]):
            dados["prioridade"] = 3

        return dados

    # --- Lógica 3: Processamento Genérico (Fallback) ---
    @staticmethod
    def _processar_generico(text: str, text_upper: str) -> dict:
        # Tenta extrair o básico se o formato for desconhecido
        cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        
        dados = {
            "tipo_doc": "DESCONHECIDO",
            "cpf": cpf_match.group(0) if cpf_match else None,
            "nome": "Extração Genérica - Verificar",
            "prioridade": 1,
            "texto_bruto_inicio": text[:200] # Debug: Mostra o começo do texto para ajudar a identificar
        }
        
        # Tenta inferir prioridade por palavras-chave mesmo sem saber o doc
        if any(t in text_upper for t in ["URGENTE", "CANCER", "ONCOLOGIA"]):
            dados["prioridade"] = 3
            
        return dados