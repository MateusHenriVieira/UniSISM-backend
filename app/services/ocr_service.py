import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import re
import io

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

        # 2. Busca de Padrões Básicos
        cpf_pattern = r'\d{3}\.\d{3}\.\d{3}-\d{2}'
        cpf_match = re.search(cpf_pattern, text)
        cpf_str = cpf_match.group(0) if cpf_match else None

        # 3. Lógica de Extração de Nome (Melhorada)
        nome_detectado = "Validar no Dashboard"
        linhas = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
        
        if cpf_str:
            for i, linha in enumerate(linhas):
                if cpf_str in linha:
                    # Geralmente o nome está na linha anterior ao CPF
                    if i > 0: nome_detectado = linhas[i-1]
                    break
                if "NOME:" in linha.upper():
                    nome_detectado = linha.split(":")[-1].strip()
                    break

        # 4. ALGORITMO DE PRIORIDADE (Novo)
        # 5: Emergência/Oncologia/Hemodiálise
        # 3: Urgente/Prioritário
        # 1: Eletivo/Rotina
        prioridade = 1 
        if any(x in text_upper for x in ["ONCOLOGIA", "CANCER", "QUIMIOTERAPIA", "HEMODIALISE", "RIM", "CARDIOPATIA GRAVE"]):
            prioridade = 5
        elif any(x in text_upper for x in ["URGENTE", "PRIORIDADE", "GESTANTE", "IDOSO"]):
            prioridade = 3
        
        return {
            "cpf": cpf_str, 
            "nome": nome_detectado, 
            "prioridade": prioridade,
            "texto_completo": text
        }