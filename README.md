# 🛰️ Systems Command Center

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white)

Um dashboard interativo e em tempo real construído com **Streamlit** para monitoramento global de infraestrutura (VMs Windows) e status de robôs de automação (RPA/APIs). O projeto apresenta uma interface visual imersiva estilo "Cyberpunk/Matrix" com feedback dinâmico de hardware e software.

## ✨ Funcionalidades

* **Monitoramento de Hardware em Tempo Real:** Integração direta com o Prometheus via PromQL para extrair dados de uso de CPU, RAM e Disco (C:) dos servidores (via Node Exporter).
* **Console de Operações de RPA:** Leitura de endpoints JSON para verificar o status de robôs de automação (ex: Apuração de Domínio, Disparo de E-mails de Cobrança).
* **UI/UX Avançada (Vibe Tech):** * Fundo animado em JavaScript nativo (Matrix Digital Rain) isolado para não interferir na performance.
    * CSS customizado com grid responsivo, cores elétricas de status (Neon Green, Amber, Electric Red) e fontes monospace (`Fira Code`).
    * Modais modulares expandidos construídos com Flexbox.
* **Arquitetura Segura:** Separação estrita de responsabilidades (UI x Lógica de Rede) e proteção de dados sensíveis da infraestrutura interna.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python
* **Frontend:** Streamlit, HTML5, CSS3, JavaScript (Canvas API)
* **Integrações:** Requests (APIs REST), Prometheus
* **Dados:** Pandas, Datetime

## 🚀 Como Executar o Projeto

**1. Clone o repositório**
```bash
git clone [https://github.com/seu-usuario/systems-command-center.git](https://github.com/seu-usuario/systems-command-center.git)
cd systems-command-center
```

**2. Instale as dependências**
```bash
pip install -r requirements.txt
```

**3. Configure o Ambiente**
Para proteger os IPs reais da infraestrutura, este repositório utiliza um arquivo de configuração de exemplo.
* Renomeie o arquivo `config_vms.exemplo.py` para `config_vms.py`.
* Edite o `config_vms.py` inserindo os IPs reais dos seus servidores e os endpoints das suas aplicações.

**4. Execute o Dashboard**
```bash
streamlit run app.py
```

## 📂 Estrutura do Projeto

```text
├── app.py                   # Frontend Streamlit e injeção de CSS/JS
├── config_vms.exemplo.py    # Template genérico de configuração das VMs e funções do Prometheus
├── nomes_vm.exemplo.py      # Dicionário de IPs e Nomes amigáveis dos servidores
├── requirements.txt         # Dependências do projeto
└── README.md
```
