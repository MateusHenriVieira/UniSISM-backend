from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext

# Configurações (Idealmente viriam de um .env)
SECRET_KEY = "UNISISM_SECRET_KEY_CHANGE_ME_IN_PROD" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)

def verificar_senha(senha_pura: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_pura, senha_hash)

def criar_token_acesso(dados: dict, tempo_expiracao: Optional[timedelta] = None):
    to_encode = dados.copy()
    if tempo_expiracao:
        expire = datetime.utcnow() + tempo_expiracao
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt