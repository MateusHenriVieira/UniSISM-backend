# criar_admin.py
from app.db.session import SessionLocal
from app.db.base import Usuario
from app.core.security import criar_hash_senha

db = SessionLocal()
cpf_admin = "000.000.000-00"

# Regra: No início, senha = cpf
senha_inicial = cpf_admin 

existe = db.query(Usuario).filter(Usuario.cpf == cpf_admin).first()
if not existe:
    print(f"Criando Admin para Primeiro Acesso...")
    novo_admin = Usuario(
        nome="Super Admin",
        cpf=cpf_admin,
        login=cpf_admin, # Login inicial é o CPF
        senha_hash=criar_hash_senha(senha_inicial), # Senha inicial é o CPF
        perfil="SUPER_ADMIN",
        primeiro_acesso=True # <--- Força a troca na primeira vez
    )
    db.add(novo_admin)
    db.commit()
    print("Admin criado! Use CPF como Login e Senha.")