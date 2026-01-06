import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .session import Base

class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpf = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    telefone = Column(String, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class CronogramaViagem(Base):
    """
    O 'Carro do BlaBlaCar': Uma viagem específica com vagas limitadas.
    """
    __tablename__ = "cronograma_viagens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    destino = Column(String, nullable=False)
    data_partida = Column(DateTime, nullable=False)
    placa = Column(String, nullable=False)
    motorista = Column(String, nullable=False)
    
    capacidade_total = Column(Integer, default=40)
    vagas_ocupadas = Column(Integer, default=0) # Só aumenta quando o gestor APROVA
    
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class SolicitacaoTFD(Base):
    """
    A 'Candidatura' à vaga.
    """
    __tablename__ = "solicitacoes_tfd"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id"))
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("cronograma_viagens.id"), nullable=True)
    
    procedimento = Column(String, nullable=True)
    data_desejada = Column(DateTime, nullable=False)
    com_acompanhante = Column(Boolean, default=False)
    
    # Prioridade extraída do PDF (5=Altíssima/Onco, 1=Baixa/Eletiva)
    nivel_prioridade = Column(Integer, default=1) 
    
    # Status: 'Aguardando_Analise', 'Aprovado_Onibus', 'Lista_Espera', 'Encaminhado_Ajuda_Custo'
    status_pedido = Column(String, default="Aguardando_Analise")
    
    valor_ajuda_custo = Column(Float, default=0.0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())