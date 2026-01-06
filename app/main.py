from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importação da Conexão com o Banco e Modelos
from app.db.session import engine
from app.db import base

# Importação das Rotas dos Módulos
from app.api.endpoints import ocr, pacientes, tfd, frota

# 1. Criação das tabelas no PostgreSQL automaticamente ao iniciar
# Isso garante que 'pacientes', 'agendamentos' e 'viagens_tfd' existam
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UniSISM - Sistema Integrado de Saúde Municipal",
    description="Plataforma de governança em saúde e logística de alta performance",
    version="1.0.0"
)

# 2. Configuração de CORS (Cross-Origin Resource Sharing)
# Essencial para permitir que o Frontend (Next.js/Tauri) acesse a API na VPS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua pelo IP da sua VPS ou domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Registro das Rotas (Endpoints)
# Módulo Médico & Secretaria: Processamento de PDFs via OCR
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR & Secretaria"])

# Módulo de Gestão de Pacientes
app.include_router(pacientes.router, prefix="/api/v1/pacientes", tags=["Pacientes"])

# Módulo de Gestão de TFD: Controle orçamentário e ajudas de custo
app.include_router(tfd.router, prefix="/api/v1/tfd", tags=["TFD & Financeiro"])

# Módulo de Frota: Vouchers de abastecimento e motoristas
app.include_router(frota.router, prefix="/api/v1/frota", tags=["Logística & Frota"])

# 4. Endpoints de Verificação do Sistema
@app.get("/")
async def root():
    """Retorna o status geral dos módulos do sistema"""
    return {
        "sistema": "UniSISM",
        "status": "Online",
        "versao": "1.0.0",
        "modulos_ativos": [
            "OCR Engine (Python/Tesseract)",
            "Gestão TFD (Controle Orçamentário)",
            "Logística de Frota (App Motorista)",
            "Mensageria (WhatsApp/Push)"
        ]
    }

@app.get("/health")
async def health_check():
    """Endpoint para monitoramento da VPS"""
    return {"status": "healthy", "database": "connected"}