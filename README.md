# 🎙️ Omni Core V2

**Sistema Modular de Automação, Monitoramento e Inteligência para Emissoras de Rádio**

O **Omni Core V2** é um ecossistema modular avançado projetado para gerenciar e automatizar os fluxos de trabalho de estações de rádio. Ele atua na integração e monitoramento de componentes de transmissão e softwares como **ZaraRadio**, **BUTT** (Broadcast Using This Tool), **vMix**, e agrega inteligência artificial via **Gemini AI** para curadoria acústica automatizada.

---

## 🏗️ Estrutura do Ecossistema

O repositório está organizado em módulos focados em suas respectivas responsabilidades:

*   [`core/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/core): Contém a lógica fundamental do sistema, o gerenciamento de banco de dados SQLite, inicializadores gráficos, constantes de tempo e helpers utilitários.
*   [`director/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/director): Camada orquestradora central. Responsável pela inicialização segura do sistema (Singleton Mutex), auditoria de integridade de logs, curadoria algorítmica e engine de montagem de playlists.
*   [`workers/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/workers) e [`services/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/services): Agentes autônomos que rodam em segundo plano executando tarefas críticas como monitoramento de recursos, sincronização, normalização e curadoria.
*   [`api/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/api) e [`routers/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/routers): API de alto desempenho construída em FastAPI para controle de workers e disponibilização de rotas de dados para o frontend.
*   [`frontend/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/frontend): Painel administrativo (Dashboard) em React moderno para monitoramento em tempo real do acervo, logs de auditoria e status de streaming.
*   [`gui/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/gui): Interface gráfica Tkinter para controle local no Windows e ícone na bandeja do sistema (System Tray).
*   [`scripts/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/scripts): Utilitários administrativos, controladores externos (como o vMix) e scripts de configuração.
*   [`tests/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/tests): Conjunto de testes unitários e de integração abrangentes.

---

## 🔒 Configuração e Segurança Integrada

Para garantir conformidade de segurança e evitar o vazamento de segredos, nenhuma credencial é armazenada no controle de versão.

### 1. Variáveis de Ambiente (`.env`)
Copie o arquivo template [`.env.example`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/.env.example) para `.env` no diretório raiz do projeto e configure suas chaves de API (Google Drive, Gemini AI, Telegram, WhatsApp, etc.):
```bash
cp .env.example .env
```

### 2. Configurações Globais (`config/settings.json`)
As definições de blocos de programação, diretórios locais e horários de execução dos workers devem ser ajustadas no arquivo `config/settings.json`. Crie-o a partir do arquivo de exemplo [`config/settings.example.json`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/config/settings.example.json).

### 3. Mecanismos de Proteção Implementados
*   **Prevenção de OS Command Injection:** Comandos de terminal externos são executados estritamente através do envio parametrizado em lista (`shell=False`).
*   **SQL Injection Blindado:** Interações com o banco de dados usam exclusivamente consultas parametrizadas do ORM SQLAlchemy.
*   **Path Traversal Mitigado:** Downloads e operações com arquivos validam e resolvem os caminhos de forma segura através do `pathlib.Path.resolve()`.
*   **Processamento XML Seguro (XXE):** Parse de dados vindos do vMix configurados para bloquear entidades externas.
*   **Blindagem do Frontend:** Componentes React como o [`NowPlayingCard.jsx`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/frontend/src/components/NowPlayingCard.jsx) tratam a desserialização de JSON via Websocket dentro de blocos defensivos `try-catch` para evitar travamentos visuais.

---

## 🚀 Como Executar

### Pré-requisitos
*   Python 3.10 ou superior instalado.
*   Instalação das dependências necessárias:
    ```bash
    pip install -r requirements.txt
    ```

### Inicialização via Windows (Recomendado)
Para facilitar o acionamento em computadores de transmissão de rádio:
1. Execute o script [`scripts/create_shortcut.py`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/scripts/create_shortcut.py) para gerar automaticamente um atalho moderno do **Omni Core V2** na sua Área de Trabalho.
2. Dê duplo clique no atalho gerado ou execute diretamente o script de lote [`START_OMNI.bat`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/START_OMNI.bat).

### Modos de Inicialização por Linha de Comando

*   **Modo Gráfico e Tray App (Padrão):**
    ```bash
    python main.py
    ```
    Isso abrirá a aplicação em bandeja do Windows com suporte a console visual e redirecionará o navegador padrão para o Dashboard Web em `http://localhost:8001`. Se o sistema já estiver em execução, ele trará o navegador de volta ao foco em vez de encerrar silenciosamente.

*   **Modo Headless (Apenas API, Sem Interface Gráfica):**
    Ideal para servidores de monitoramento dedicados.
    ```bash
    python main.py --headless
    ```

---

## 🛠️ Detalhes dos Workers Ativos

O comportamento autônomo do Omni Core é mantido por workers específicos definidos em [`workers/`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/workers):

*   **GuardianWorker:** Monitora o hardware do sistema (CPU/RAM) e processos de rádio (ZaraRadio/BUTT). Bloqueia tentativas automáticas de atualização ou reinício do Windows em horários críticos e reativa conexões de streaming perdidas.
*   **CuradoriaWorker:** Utiliza inteligência acústica e inteligência artificial para ler metadados das faixas no acervo, catalogar BPM, energia e classificar humor das músicas.
*   **PlaylistWorker:** Gera diariamente as grades de programação baseadas em regras de alternância e regras do acervo.
*   **BulletinWorker:** Realiza o download e sincronização dinâmica de arquivos de boletins jornalísticos atualizados a partir do Google Drive da emissora.
*   **WeatherWorker:** Consome dados meteorológicos para geração de previsões rápidas no painel de controle.
*   **AuditWorker:** Analisa retroativamente o histórico de execução de músicas para relatórios de compliance.

---

## 🧪 Executando Testes

Para rodar os testes unitários e de integração e validar as regras do sistema:
```bash
pytest
```

---

## 📖 Outros Guias e Documentações
*   [`OPERACAO.md`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/OPERACAO.md): Guia voltado a operadores e suporte técnico.
*   [`GUIA_RAPIDO.md`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/GUIA_RAPIDO.md): Introdução rápida de comandos.
*   [`MODULARIZATION_ROADMAP.md`](file:///c:/Users/STREAMING/.gemini/antigravity/scratch/radio_manager_agent/MODULARIZATION_ROADMAP.md): Registro da evolução e refatoração arquitetural do Omni Core V2.
