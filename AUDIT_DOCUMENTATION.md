# AUDIT DOCUMENTATION - OMNI CORE V2 🥒

Este documento descreve a arquitetura técnica, o esquema de dados e os fluxos de comunicação do sistema Omni Core V2.

## 1. Esquema do Banco de Dados (SQLite)

O sistema utiliza SQLAlchemy para ORM. O banco de dados principal está localizado em `core/radio_omni.db`.

### Tabela: `musicas`
Armazena o acervo musical e metadados de curadoria.
- `id`: Identificador único (Integer).
- `caminho`: Caminho absoluto do arquivo (String, Unique).
- `artista` / `titulo`: Metadados básicos limpos pelo `artist_cleaner`.
- `estilo` / `energia` / `bpm`: Atributos musicais para dayparting.
- `valence` / `danceability`: Atributos de humor/ritmo extraídos via Librosa.
- `auditado_acustica`: Flag de curadoria técnica (Boolean).
- `redflag`: Marcador de conteúdo impróprio ou falha acústica (Boolean).
- `mood`: Humor da música (Ensolarado, Chuvoso, Nublado).
- `ultima_reproducao`: Timestamp da última vez que tocou (UTC).
- `vezes_tocada`: Contador de execuções para fair-rotation.
- `quarantine_reason`: Motivo se a música estiver em quarentena técnica.

### Tabela: `regras_programacao`
Define como a rádio deve se comportar em diferentes horários.
- `bloco`: Nome do bloco (Madrugada, Manhã, Tarde, Noite).
- `hora_inicio` / `hora_fim`: Janela de tempo de 24h.
- `energia_alvo`: Nível de energia desejado para o bloco (1-5).

---

## 2. Lista de Workers (Agentes de Execução)

Os workers são gerenciados pelo `WorkerManager` e executados em threads de background via `APScheduler`.

| Worker | Função |
| :--- | :--- |
| **GuardianWorker** | Watchdog do sistema. Realiza verificações de alta frequência (2s) para garantir estabilidade de áudio e processos. |
| **CuradoriaWorker** | Processa novas músicas, limpa metadados e aplica análise acústica (Librosa) para quarentena. |
| **WeatherWorker** | Consulta APIs de clima para ajustar dinamicamente o `CURRENT_MOOD` da rádio. |
| **SyncWorker** | Sincroniza o acervo físico com os registros do banco de dados. |
| **AuditWorker** | Verifica conformidade das playlists com as regras de separação de artistas e faixas. |
| **PlaylistWorker** | Motor principal de geração de blocos musicais diários de 24h (Cron 00:00). |
| **ButtWorker** | Monitora e reconecta instâncias do streamer (BUTT) em caso de queda de conexão. |
| **UpdateWorker** | Verifica atualizações no repositório e sinaliza necessidade de rebuild. |
| **DailyReportWorker** | Consolida métricas de 'cycles' e performance para relatório via WhatsApp (18:00). |
| **BulletinWorker** | Sincroniza boletins informativos do Google Drive para a pasta local de exibição. |
| **DownloaderWorker** | Adquire novas faixas proativamente (YouTube/AI) durante a madrugada. |
| **ApiWorker** | Worker de auto-recuperação que monitora a saúde do servidor FastAPI na porta 8001. |
| **NotificationWorker** | Gerencia o sistema de alertas externos e envio de Heartbeats. |
| **Playlist Maintenance** | Job horária que garante a existência de blocos futuros, prevenindo o silêncio da rádio. |

---

## 3. Fluxo de Comunicação e Telemetria

A arquitetura de comunicação é baseada em eventos assíncronos e arquitetura REST.

### Fluxo: API -> Dashboard (Real-time)
1. O **Dashboard (Vite/React)** estabelece conexão **WebSocket (`/ws/status`)**.
2. O servidor envia heartbeats a cada 30 segundos para manter o túnel TCP aberto.
3. Ciclo de Evento:
   - Um **Worker** finaliza sua tarefa no `worker_manager.py`.
   - O `run_cycle` invoca `api.manager.broadcast_event`.
   - O evento (status, score, metadata) é transmitido via WebSocket.
   - A UI reage instantaneamente exibindo o log descritivo (via `RewardStore.generate_description`).

### Fluxo: Logs de Sistema
- O backend centraliza logs em `logs/omni_system.log` e logs diários datados.
- O endpoint `GET /api/status/logs/system` permite o tailing das últimas 50 linhas para depuração remota.

### Fluxo: Controle (Frontend -> API)
1. Requisições RESTful para controle de workers e configurações.
2. Persistência via `SessionLocal` (Thread-safe scoping).
3. Mudanças de estado são refletidas no próximo ciclo de execução dos workers.

---

## 4. Estratégia Headless e Ocultação

- **Boot**: Iniciado via `START_OMNI.bat` usando `start /B pythonw main.py`.
- **UI**: Tkinter inicializado com `root.withdraw()` imediato. A interface é acessível apenas via Tray Icon (ícone da bandeja) ou Dashboard Web.
- **Processos**: Subprocessos de sistema (FFmpeg, API) são disparados com flags `CREATE_NO_WINDOW` no Windows.

---
*Documentação mestre gerada por Pickle Rick. Wubba Lubba Dub Dub!* 🥒
