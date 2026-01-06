# UniSISM - Sistema Integrado de Saúde Municipal 🏥🚌

O **UniSISM** é uma plataforma de governança em saúde e logística de alta performance, desenvolvida para unificar o fluxo de atendimento médico, o processamento administrativo da Secretaria de Saúde e a operação de transporte de pacientes (TFD).

O sistema foi arquitetado para substituir processos manuais por fluxos automatizados baseados em **OCR (Visão Computacional)** e **Mensageria Inteligente**.

---

## 🎯 Problemas Resolvidos e Mitigados

O UniSISM ataca diretamente as ineficiências históricas da gestão pública municipal:

* **Gargalo de Comunicação:** Elimina a perda de exames por falta de aviso ao paciente através de notificações duplas (WhatsApp e App).
* **Erro de Digitação e Processamento:** O uso de **OCR** para extrair dados de PDFs do SUS remove a falha humana e acelera o processamento em 80%.
* **Descontrole Financeiro no TFD:** Impede o esgotamento do teto de "ajuda de custo" através de um algoritmo de rateio diário e travas de aprovação humana.
* **Fraudes e Desperdício em Combustível:** O controle rigoroso de vouchers de abastecimento vinculados a placas e motoristas impede desvios de recursos.
* **Ociosidade Logística:** O sistema de reserva de assentos e a chamada digital garantem que o transporte seja otimizado e que a presença seja auditada.

---

## 📈 Ganhos Estratégicos

### 💰 Ganhos Financeiros

* **Controle Orçamentário Estrito:** Implementação de teto diário para ajudas de custo (Ex: Divisão proporcional de R$ 5.000,00/mês), evitando gastos acima da arrecadação.
* **Auditoria de Frota:** Redução de custos operacionais com combustíveis através do registro detalhado de quilometragem, litros e tipo de combustível por viagem.
* **Eficiência de RH:** Redução da carga horária dedicada a tarefas repetitivas (redigitação e telefone), permitindo que a equipe foque em atendimento humano.

### 🏛️ Ganhos Políticos

* **Transparência e Cidadania:** O rastreio "Estilo Shopee" dá ao cidadão a sensação de acompanhamento real, reduzindo reclamações e aumentando a confiança na gestão.
* **Modernização da Máquina:** Posiciona a prefeitura como uma referência tecnológica e inovadora na região.
* **Governança Segura:** O envolvimento de figuras chave na aprovação (como **Aurélia**) garante que recursos críticos passem por uma camada de vigilância de confiança.

### ⚙️ Ganhos Organizacionais

* **Unificação de Dados:** Fim das planilhas isoladas; médico, secretaria e TFD utilizam a mesma "fonte da verdade".
* **Histórico Digital:** Prontuário de viagens e exames acessível em segundos, facilitando auditorias e tomadas de decisão baseadas em dados (BI).

---

## 🏗️ Arquitetura e Módulos

### 1. Módulo Médico & Secretaria

* **Input Clínico:** Cadastro de consultas/exames.
* **Processamento SUS:** Upload de PDFs e **OCR Engine** (Python) para extração automática de CPF, Telefone, Local e Data.
* **Verificador de Atividade:** O sistema checa via CPF se o paciente possui o App ativo para decidir o canal de notificação.

### 2. Super App do Paciente

* **Status Tracking:** Barra de progresso visual (estilo entrega Shopee) do agendamento.
* **Central de Logística:** Solicitação de viagem e acompanhamento de status (Aguardando Liberação / Confirmado).
* **Ticket de Viagem:** Dados do motorista, placa do veículo e número da poltrona.

### 3. Gestão de TFD & Frota (Painel Admin)

* **Workflow de Aprovação:** Sistema de travas para ajuda de custo e viagens, exigindo liberação manual (Gestora TFD/Aurélia).
* **Voucher de Abastecimento:** Geração de comprovante com validade, placa, motorista e quilometragem.

### 4. App do Motorista

* **Chamada Digital:** Lista de passageiros autorizados para check-in no embarque.
* **Sync de Presença:** Atualização automática da situação do paciente (Presente/Falta) para consulta da Secretaria.

---

## 🛠️ Stack Técnica

* **Backend:** Python (FastAPI/Flask) + PostgreSQL.
* **Desktop Admin:** Next.js + Tauri (Nativo Windows para secretaria).
* **Mobile:** React (Android/iOS para Paciente e Motorista).
* **Infra:** VPS Dedicada + API WhatsApp + Firebase (Push Notifications).

---

**UniSISM: Tecnologia que cuida, gestão que controla.**
