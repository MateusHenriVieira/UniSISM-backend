import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Boolean, Integer, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .session import Base

# Tabela de associação: Médico <-> Unidades de Saúde
# (Permite que o Dr. Fernando atenda na UBS Centro de manhã e na UBS Vila à tarde)
medico_unidade = Table(
    'medico_unidades',
    Base.metadata,
    Column('usuario_id', UUID(as_uuid=True), ForeignKey('usuarios.id')),
    Column('unidade_id', UUID(as_uuid=True), ForeignKey('unidades_saude.id'))
)

class UnidadeSaude(Base):
    __tablename__ = "unidades_saude"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False) # Ex: UBS Vila Ferreira
    bairro = Column(String, nullable=False)
    
    # Cota de Vagas (Para gestão da secretaria)
    cota_mensal = Column(Integer, default=50) 
    
    medicos = relationship("Usuario", secondary=medico_unidade, back_populates="unidades")
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class Usuario(Base):
    """
    Pode ser Médico, Enfermeiro ou Admin.
    """
    __tablename__ = "usuarios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False)
    cpf = Column(String, unique=True, index=True, nullable=False)
    crm = Column(String, nullable=True) # Só para médicos
    senha_hash = Column(String, nullable=False) # Para futuro login
    
    # Perfil: 'MEDICO', 'RECEPCAO_UBS', 'GESTOR_TFD'
    perfil = Column(String, default="MEDICO")
    
    unidades = relationship("UnidadeSaude", secondary=medico_unidade, back_populates="medicos")
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpf = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    telefone = Column(String, nullable=True)
    
    # Vincula o paciente à unidade de origem (Onde ele tem prontuário)
    unidade_origem_id = Column(UUID(as_uuid=True), ForeignKey("unidades_saude.id"), nullable=True)
    
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class CronogramaViagem(Base):
    __tablename__ = "cronograma_viagens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destino = Column(String, nullable=False)
    data_partida = Column(DateTime, nullable=False)
    placa = Column(String, nullable=False)
    motorista = Column(String, nullable=False)
    capacidade_total = Column(Integer, default=40)
    vagas_ocupadas = Column(Integer, default=0)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class SolicitacaoTFD(Base):
    __tablename__ = "solicitacoes_tfd"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paciente_id = Column(UUID(as_uuid=True), ForeignKey("pacientes.id"))
    viagem_id = Column(UUID(as_uuid=True), ForeignKey("cronograma_viagens.id"), nullable=True)
    
    # RASTREABILIDADE TOTAL (Quem solicitou e de onde)
    medico_solicitante_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    unidade_solicitante_id = Column(UUID(as_uuid=True), ForeignKey("unidades_saude.id"), nullable=True)
    
    procedimento = Column(String, nullable=True)
    data_desejada = Column(DateTime, nullable=False)
    com_acompanhante = Column(Boolean, default=False)
    nivel_prioridade = Column(Integer, default=1) 
    status_pedido = Column(String, default="Aguardando_Analise")
    tipo_transporte = Column(String, default="Pendente") 
    valor_ajuda_custo = Column(Float, default=0.0)
    
    status_aprovacao = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())