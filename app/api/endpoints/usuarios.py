from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.db.session import get_db
from app.db.base import Usuario, UnidadeSaude
from app.core.security import criar_hash_senha
from app.api.deps import ChecarPermissao
from app.schemas.usuario import UsuarioCreate, UsuarioResponse, UsuarioUpdate

router = APIRouter()

# Dependência de Segurança: SÓ SUPER ADMIN ENTRA AQUI
permissao_super_admin = ChecarPermissao(["SUPER_ADMIN"])

@router.post("/", response_model=UsuarioResponse, dependencies=[Depends(permissao_super_admin)])
async def criar_usuario(
    usuario_in: UsuarioCreate,
    db: Session = Depends(get_db)
):
    """
    Cria um novo usuário no sistema.
    - Senha inicial = CPF (Login = CPF).
    - Define primeiro_acesso = True.
    """
    # 1. Verifica se CPF já existe
    if db.query(Usuario).filter(Usuario.cpf == usuario_in.cpf).first():
        raise HTTPException(400, "CPF já cadastrado.")

    # 2. Prepara a Senha Inicial (Regra: Senha = CPF)
    senha_hash = criar_hash_senha(usuario_in.cpf)

    # 3. Cria o Objeto Usuário
    novo_usuario = Usuario(
        nome=usuario_in.nome,
        cpf=usuario_in.cpf,
        login=usuario_in.cpf, # Login inicial
        senha_hash=senha_hash,
        perfil=usuario_in.perfil.upper(),
        crm=usuario_in.crm,
        primeiro_acesso=True
    )

    # 4. Vínculo com Unidades de Saúde (Se fornecido)
    if usuario_in.unidades_ids:
        for unidade_id in usuario_in.unidades_ids:
            unidade = db.query(UnidadeSaude).filter(UnidadeSaude.id == unidade_id).first()
            if unidade:
                novo_usuario.unidades.append(unidade)

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    # Monta resposta manual para incluir as unidades formatadas
    return formatar_retorno(novo_usuario)

@router.get("/", response_model=List[UsuarioResponse], dependencies=[Depends(permissao_super_admin)])
async def listar_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).offset(skip).limit(limit).all()
    return [formatar_retorno(u) for u in usuarios]

@router.put("/{user_id}/reset-senha", dependencies=[Depends(permissao_super_admin)])
async def resetar_senha(user_id: str, db: Session = Depends(get_db)):
    """
    Reseta a senha do usuário para o CPF dele e ativa 'primeiro_acesso'.
    Útil quando o médico esquece a senha.
    """
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario: raise HTTPException(404, "Usuário não encontrado")
    
    usuario.senha_hash = criar_hash_senha(usuario.cpf)
    usuario.login = usuario.cpf
    usuario.primeiro_acesso = True
    
    db.commit()
    return {"message": f"Senha resetada com sucesso para o CPF: {usuario.cpf}"}

def formatar_retorno(usuario):
    """Helper para formatar o objeto SQLAlchemy para o Schema Pydantic"""
    return {
        "id": str(usuario.id),
        "nome": usuario.nome,
        "cpf": usuario.cpf,
        "login": usuario.login,
        "perfil": usuario.perfil,
        "crm": usuario.crm,
        "primeiro_acesso": usuario.primeiro_acesso,
        "criado_em": usuario.criado_em,
        "unidades": [{"id": str(u.id), "nome": u.nome} for u in usuario.unidades]
    }