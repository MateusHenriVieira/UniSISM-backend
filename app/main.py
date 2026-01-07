from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importação da Conexão e Banco
from app.db.session import engine
from app.db import base

# Importação dos Módulos (Endpoints)
# ATUALIZADO: Adicionado 'usuarios' para gestão de acesso
from app.api.endpoints import auth, ocr, pacientes, tfd, frota, medico, usuarios

# 1. Inicialização do Banco de Dados
# Cria tabelas se não existirem (Usuario, UnidadeSaude, SolicitacaoTFD, etc.)
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UniSISM - Sistema Integrado de Saúde Municipal",
    description="Plataforma Governamental de Regulação, TFD e Gestão de Frota.",
    version="1.3.0-admin" # Versão atualizada com módulo de Gestão
)

# 2. Configuração de CORS
# Permite que o Frontend acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Registro de Rotas (Router)

# Autenticação e Primeiro Acesso
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticação & Segurança"])

# Gestão de Usuários (NOVO: Painel do Super Admin)
app.include_router(usuarios.router, prefix="/api/v1/usuarios", tags=["Gestão de Usuários (Admin)"])

# Portal do Médico (Dashboard e Seleção de UBS)
app.include_router(medico.router, prefix="/api/v1/medico", tags=["Portal do Médico"])

# Inteligência de Entrada (OCR Híbrido)
app.include_router(ocr.router, prefix="/api/v1/ocr", tags=["OCR & Documentos"])

# Regulação TFD (Prioridade e BlaBlaCar da Saúde)
app.include_router(tfd.router, prefix="/api/v1/tfd", tags=["Regulação TFD"])

# Gestão de Frota (Ônibus e Motoristas)
app.include_router(frota.router, prefix="/api/v1/frota", tags=["Logística & Frota"])

# Gestão Básica de Pacientes
app.include_router(pacientes.router, prefix="/api/v1/pacientes", tags=["Pacientes"])

# 4. Status do Sistema
@app.get("/")
async def root():
    return {
        "sistema": "UniSISM",
        "status": "Online",
        "versao": "1.3.0",
        "seguranca": "RBAC + Primeiro Acesso Obrigatório",
        "modulos": [
            "Auth (JWT/Bcrypt)",
            "Gestão de Usuários (Admin)", # <--- Módulo novo listado
            "OCR Engine v2",
            "Portal Médico",
            "TFD Inteligente"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}