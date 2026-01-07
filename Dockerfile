# Use uma imagem oficial do Python leve e segura
FROM python:3.11-slim

# 1. Instalar dependências do Sistema Operacional
# ATUALIZAÇÃO: Substituímos 'libgl1-mesa-glx' (obsoleto) por 'libgl1' e 'libglib2.0-0'
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# 2. Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Comando de entrada
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]