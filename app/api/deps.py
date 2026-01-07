from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import SECRET_KEY, ALGORITHM
from app.db.base import Usuario

# Define a rota onde o frontend deve pegar o token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_usuario_atual(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Decodifica o Token JWT e busca o usuário no banco.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        cpf: str = payload.get("sub")
        if cpf is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(Usuario).filter(Usuario.cpf == cpf).first()
    if user is None:
        raise credentials_exception
    return user

class ChecarPermissao:
    """
    Valida se o usuário tem o perfil necessário para acessar a rota.
    Uso: dependencies=[Depends(ChecarPermissao(["ADMIN"]))]
    """
    def __init__(self, perfis_permitidos: list):
        self.perfis_permitidos = perfis_permitidos

    def __call__(self, usuario: Usuario = Depends(get_usuario_atual)):
        # SUPER_ADMIN tem passe livre para tudo
        if usuario.perfil == "SUPER_ADMIN":
            return usuario
            
        if usuario.perfil not in self.perfis_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Acesso negado. Seu perfil ({usuario.perfil}) não tem permissão para este recurso."
            )
        return usuario