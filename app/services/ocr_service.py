import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import re
import io
import logging

logger = logging.getLogger(__name__)

class OCRService:
    @staticmethod
    def extrair_dados_sus(file_bytes, filename):
        text = ""
        
        # 1. Conversão PDF/Imagem
        if filename.lower().endswith(".pdf"):
            images = convert_from_bytes(file_bytes)
            for img in images:
                text += pytesseract.image_to_string(img, lang='por')
        else:
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image, lang='por')
        
        text_upper = text.upper()
        
        # 2. Roteamento Inteligente: Qual documento é esse?
        if "COMPROVANTE DE AGENDAMENTO" in text_upper:
            logger.info("OCR detectou: Comprovante de Agendamento (Volta do SUS)")
            return OCRService._processar_comprovante_agendamento(text, text_upper)
        
        elif "LAUDO PARA SOLICITAÇÃO" in text_upper or "PROCEDIMENTO AMBULATORIAL" in text_upper:
            logger.info("OCR detectou: Laudo Médico (Pedido do Doutor)")
            return OCRService._processar_laudo_medico(text, text_upper)
        
        else:
            # Tenta um genérico se não reconhecer o cabeçalho
            return OCRService._processar_generico(text, text_upper)

    # --- Lógica 1: O documento que você mandou ANTES (Agendamento Confirmado) ---
    @staticmethod
    def _processar_comprovante_agendamento(text, text_upper):
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

        # Extração Específica do Comprovante de Garanhuns
        cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        if cpf_match: dados["cpf"] = cpf_match.group(0)

        nome_match = re.search(r'NOME:\s*(.*)', text_upper)
        if nome_match: dados["nome"] = nome_match.group(1).split("TELEFONE")[0].strip()

        data_match = re.search(r'DATA:\s*(\d{2}/\d{2}/\d{4})', text_upper)
        if data_match: dados["data_exame"] = data_match.group(1)

        hora_match = re.search(r'HORA:\s*(\d{2}:\d{2})', text_upper)
        if hora_match: dados["hora_exame"] = hora_match.group(1)
        
        # Destino
        if "GARANHUNS" in text_upper: dados["destino_detectado"] = "GARANHUNS"
        elif "RECIFE" in text_upper: dados["destino_detectado"] = "RECIFE"

        # Prioridade baseada no procedimento agendado
        proc_match = re.search(r'ITEM AGENDAMENTO:\s*(.*)', text_upper)
        if proc_match: 
            dados["procedimento"] = proc_match.group(1).strip()
            # Se já está agendado, a prioridade segue o procedimento
            if "ONCOLOGIA" in dados["procedimento"]: dados["prioridade"] = 5
        
        return dados

    # --- Lógica 2: O documento que você mandou AGORA (Laudo do Médico) ---
    @staticmethod
    def _processar_laudo_medico(text, text_upper):
        dados = {
            "tipo_doc": "LAUDO_SOLICITACAO", # Importante para o frontend saber
            "cpf": None,
            "nome": "Validar no Dashboard",
            "data_exame": None, # Laudo não tem data de viagem ainda
            "procedimento": None,
            "prioridade": 1,
            "telefone": None,
            "cid": None
        }

        # 1. CPF (Geralmente no rodapé ou cabeçalho do laudo)
        cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        if cpf_match: dados["cpf"] = cpf_match.group(0)

        # 2. Nome (Geralmente abaixo de "Nome do cidadão")
        # A lógica aqui procura a linha seguinte ao label
        linhas = text.split('\n')
        for i, linha in enumerate(linhas):
            if "Nome do cidadão" in linha:
                if i + 1 < len(linhas):
                    # Pega a próxima linha que não esteja vazia
                    dados["nome"] = linhas[i+1].strip() or linhas[i+2].strip()
                break
        
        # 3. Telefone (No laudo do Fernando está no cabeçalho)
        tel_match = re.search(r'Telefone\s*([\(\)0-9\-\s]+)', text) # Case sensitive as vezes ajuda
        if tel_match: dados["telefone"] = tel_match.group(1).strip()

        # 4. Procedimento Solicitado (Texto Roxo na imagem)
        # Procura por "PROCEDIMENTO SOLICITADO" e pega o texto abaixo
        for i, linha in enumerate(linhas):
            if "PROCEDIMENTO SOLICITADO" in linha.upper():
                if i + 1 < len(linhas):
                    dados["procedimento"] = linhas[i+1].strip()
                break

        # 5. ANÁLISE DE RISCO (CID10 e Justificativa) -> O MAIS IMPORTANTE
        # Captura o CID (Ex: C61)
        cid_match = re.search(r'CID10\s*([A-Z]\d{2,3}|.*)', text_upper)
        if cid_match:
            dados["cid"] = cid_match.group(1).split("-")[0].strip() # Pega só o código ou descrição curta

        # Regras de Prioridade para o Laudo
        # Se tiver CID C* (Câncer) ou D0* (Carcinoma in situ) -> Prioridade 5
        # Se tiver "Neoplasia", "Maligna" -> Prioridade 5
        texto_analise = text_upper
        if dados["cid"] and dados["cid"].startswith("C"):
            dados["prioridade"] = 5
        elif any(t in texto_analise for t in ["NEOPLASIA MALIGNA", "CANCER", "ONCOLOGIA", "HEMODIALISE"]):
            dados["prioridade"] = 5
        elif any(t in texto_analise for t in ["URGENTE", "PRIORIDADE", "RISCO"]):
            dados["prioridade"] = 3

        return dados

    @staticmethod
    def _processar_generico(text, text_upper):
        # Fallback para documentos desconhecidos (mantém lógica antiga simples)
        cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        dados = {
            "tipo_doc": "DESCONHECIDO",
            "cpf": cpf_match.group(0) if cpf_match else None,
            "nome": "Extração Genérica",
            "prioridade": 1
        }
        return dados