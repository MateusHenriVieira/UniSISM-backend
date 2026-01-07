from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import criar_token_acesso, verificar_senha, criar_hash_senha, ACCESS_TOKEN_EXPIRE_MINUTES
from app.db.base import Usuario
from app.api.deps import get_usuario_atual # Dependência de usuário logado
from pydantic import BaseModel

router = APIRouter()

# --- Schemas ---
class LoginSchema(BaseModel):
    login: str # Pode ser CPF ou o Login escolhido
    senha: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    primeiro_acesso: bool # Flag vital para o Frontend
    perfil: str
    nome: str

class TrocaCredenciaisSchema(BaseModel):
    novo_login: str
    nova_senha: str

# --- 1. Rota de Login ---
@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: LoginSchema, 
    db: Session = Depends(get_db)
):
    """
    Login Unificado.
    - No 1º acesso: Login é o CPF e Senha é o CPF.
    - Retorna flag 'primeiro_acesso=True' para forçar o frontend a abrir a tela de troca.
    """
    # Busca por Login OU CPF (para garantir compatibilidade)
    usuario = db.query(Usuario).filter(
        (Usuario.login == form_data.login) | (Usuario.cpf == form_data.login)
    ).first()
    
    if not usuario:
        raise HTTPException(status_code=400, detail="Credenciais inválidas.")
    
    # Verifica a Senha
    if not verificar_senha(form_data.senha, usuario.senha_hash):
        raise HTTPException(status_code=400, detail="Credenciais inválidas.")

    # Gera o Token
    tempo_token = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = criar_token_acesso(
        dados={"sub": usuario.cpf, "perfil": usuario.perfil, "id": str(usuario.id)},
        tempo_expiracao=tempo_token
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "primeiro_acesso": usuario.primeiro_acesso, # <--- O FRONTEND DEVE OLHAR ISSO
        "perfil": usuario.perfil,
        "nome": usuario.nome
    }

# --- 2. Rota de Configuração Inicial (Troca de Senha) ---
@router.post("/definir-credenciais")
async def definir_primeiras_credenciais(
    dados: TrocaCredenciaisSchema,
    usuario_atual: Usuario = Depends(get_usuario_atual), # Precisa estar logado (com a senha provisória)
    db: Session = Depends(get_db)
):
    """
    Obrigatório após o primeiro login.
    O usuário define seu Login personalizado e sua Nova Senha.
    """
    if not usuario_atual.primeiro_acesso:
        raise HTTPException(status_code=400, detail="Você já configurou suas credenciais.")

    # Verifica se o novo login já existe (e não é o dele mesmo)
    login_existente = db.query(Usuario).filter(Usuario.login == dados.novo_login).first()
    if login_existente and login_existente.id != usuario_atual.id:
        raise HTTPException(status_code=400, detail="Este login já está em uso. Escolha outro.")

    # Atualiza os dados
    usuario_atual.login = dados.novo_login
    usuario_atual.senha_hash = criar_hash_senha(dados.nova_senha)
    usuario_atual.primeiro_acesso = False # Trava o primeiro acesso
    
    db.commit()
    
    return {"message": "Credenciais configuradas com sucesso! Faça login novamente."}

# --- 3. Rota de Perfil (Opcional) ---
@router.get("/me")
async def ler_usuario_atual(usuario_atual: Usuario = Depends(get_usuario_atual)):
    return {
        "id": str(usuario_atual.id),
        "cpf": usuario_atual.cpf,
        "login": usuario_atual.login,
        "nome": usuario_atual.nome,
        "perfil": usuario_atual.perfil,
        "unidades": [{"id": str(u.id), "nome": u.nome} for u in usuario_atual.unidades]
    }