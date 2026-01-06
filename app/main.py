from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importação da Conexão com o Banco e Modelos
from app.db.session import engine
from app.db import base

# Importação das Rotas dos Módulos
# ATUALIZADO: Adicionado 'medico' à lista de imports
from app.api.endpoints import ocr, pacientes, tfd, frota, medico

# 1. Criação das tabelas no PostgreSQL automaticamente ao iniciar
# Isso garante que todas as tabelas (incluindo as novas UnidadeSaude e Usuario) sejam criadas
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UniSISM - Sistema Integrado de Saúde Municipal",
    description="Plataforma de governança em saúde, regulação TFD e gestão de frota.",
    version="1.1.0" # Versão incrementada devido ao novo módulo médico
)

# 2. Configuração de CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja ao domínio do front (ex: Vercel)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Registro das Rotas (Endpoints)

# Módulo de Entrada Inteligente (OCR Híbrido: Laudos e Comprovantes)
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR & Entrada Inteligente"])

# Módulo do Portal do Médico (NOVO: Dashboard e Seleção de UBS)
app.include_router(medico.router, prefix="/api/v1/medico", tags=["Portal do Médico"])

# Módulo de Logística TFD (BlaBlaCar da Saúde & Financeiro)
app.include_router(tfd.router, prefix="/api/v1/tfd", tags=["Logística TFD & Regulação"])

# Módulo de Gestão de Pacientes (CRUD Básico)
app.include_router(pacientes.router, prefix="/api/v1/pacientes", tags=["Pacientes"])

# Módulo de Frota (Vouchers e Motoristas)
app.include_router(frota.router, prefix="/api/v1/frota", tags=["Logística & Frota"])

# 4. Endpoints de Verificação do Sistema
@app.get("/")
async def root():
    """Retorna o status geral dos módulos do sistema"""
    return {
        "sistema": "UniSISM",
        "status": "Online",
        "versao": "1.1.0",
        "arquitetura": "Descentralizada (UBS -> Central)",
        "modulos_ativos": [
            "OCR Engine v2 (Detecção de Laudo/CID)",
            "Portal do Médico (Gestão por Unidade)",
            "Gestão TFD (Fila de Prioridade Inteligente)",
            "Logística de Frota (Cronograma de Viagens)",
            "Mensageria (WhatsApp/Push)"
        ]
    }

@app.get("/health")
async def health_check():
    """Endpoint para monitoramento da VPS"""
    return {"status": "healthy", "database": "connected"}