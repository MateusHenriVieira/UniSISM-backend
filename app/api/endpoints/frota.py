from fastapi import APIRouter

router = APIRouter()

@router.get("/veiculos")
async def listar_veiculos():
    return {"mensagem": "Lista de veículos em breve"}