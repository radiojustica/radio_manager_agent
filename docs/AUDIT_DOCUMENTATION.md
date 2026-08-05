# AUDIT_DOCUMENTATION.md
# Omni Core V2 — Documento Mestre de Auditoria 🥒

**Projeto:** Omni Core V2 — Radio Station Intelligence  
**Repositório:** `radiojustica/radio_manager_agent`  
**Versão:** 2.1.0  \
**Última atualização:** 2026-08-04  \
**Responsável:** Pickle Rick (Lead Architect)  
**Status:** ✅ Operacional

---

## 1. Visão Geral do Sistema

O Omni Core V2 é um backend autônomo de automação para a Rádio Justiça, rodando em Windows (Python 3.14). Integra **ZaraRadio** (automação de playlist), **BUTT** (encoder de streaming), **vMix** (produção de vídeo) e **Google Drive** (sincronização de boletins). Opera 24/7 sem intervenção humana, reportando telemetria em tempo real via dashboard web.

**Princípio de design:** invisível no desktop, transparente no dashboard.

---

## 2. Arquitetura de Componentes

```
main.py / START_OMNI.bat
    └── director/orchestrator.py  (SystemOrchestrator)
            ├── core/system.py        (Admin, Mutex, Wake Lock)
            ├── api/manager.py        (FastAPI + WebSocket hub)
            ├── worker_manager.py     (WorkerManager + APScheduler)
            │       └── workers/*.py  (14 workers autônomos)
            ├── services/guardian_service.py
            ├── gui/tray.py           (System Tray — única UI visível)
            └── gui/console.py        (Tkinter oculto — apenas callback)
```

### 2.1 Stack Técnica

| Camada | Tecnologia | Função |
|--------|-----------|--------|
| Backend | FastAPI + Uvicorn | API REST + WebSocket |
| Frontend | React.js (Vite) | Dashboard web (porta 8001) |
| Banco de dados | SQLite (SQLAlchemy) | ~8.000 faixas com metadados |
| Scheduler | APScheduler | Orquestração de jobs dos workers |
| UI Desktop | pystray + Tkinter oculto | System tray; sem janelas visíveis |
| Análise de áudio | Librosa + SoundFile | BPM, energia, mood das faixas |
| Integração vMix | HTTP (porta 8088) | Gatilho de cenas automático |
| Integração GDrive | Google Drive API | Sync de boletins jornalísticos |

---

## 3. Esquema do Banco de Dados (SQLite)

O sistema utiliza SQLAlchemy para ORM. Banco em `core/radio_omni.db`.

### Tabela: `musicas`
Armazena o acervo musical e metadados de curadoria.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer | Identificador único |
| `caminho` | String (Unique) | Caminho absoluto do arquivo |
| `artista` / `titulo` | String | Metadados limpos pelo `artist_cleaner` |
| `estilo` / `energia` / `bpm` | String/Float | Atributos musicais para dayparting |
| `valence` / `danceability` | Float | Humor/ritmo extraídos via Librosa |
| `auditado_acustica` | Boolean | Flag de curadoria técnica |
| `redflag` | Boolean | Conteúdo impróprio ou falha acústica |
| `mood` | String | Ensolarado / Chuvoso / Nublado |
| `ultima_reproducao` | DateTime (UTC) | Última execução (fair-rotation) |
| `vezes_tocada` | Integer | Contador de execuções |
| `quarantine_reason` | String | Motivo de quarentena técnica |

### Tabela: `regras_programacao`
Define o comportamento da rádio por horário.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `bloco` | String | Madrugada / Manhã / Tarde / Noite |
| `hora_inicio` / `hora_fim` | Integer | Janela de 24h |
| `energia_alvo` | Integer (1-5) | Nível de energia desejado para o bloco |

---

## 4. Catálogo de Workers

Cada worker herda de `WorkerBase` e registra resultados no `RewardStore`.

| Worker | Frequência | Função | Score ✓/✗ |
|--------|-----------|--------|-----------|
| `GuardianWorker` | 30s + 2s (alta freq) | Watchdog: monitora ZaraRadio e BUTT; previne reboot | +15 / -8 |
| `ButtWorker` | 2 min | Reconecta encoder BUTT se cair | +10 / -5 |
| `CuradoriaWorker` | 5 min | Analisa BPM/energia/mood; move faixas para quarentena | +10 / -5 |
| `WeatherWorker` | 30 min | Consulta clima de Natal/RN; define `CURRENT_MOOD` | +5 / -3 |
| `BulletinWorker` | 30 min | Sincroniza boletins GDrive → `D:\SERVIDOR\BOLETINS` | +15 / -5 |
| `AuditWorker` | 1h | Verifica conformidade das playlists e integridade do DB | +10 / -5 |
| `UpdateWorker` | 1h | Verifica atualizações; sinaliza necessidade de rebuild | +5 / -2 |
| `ApiWorker` | 30s | Health check da API; mantém WebSocket vivo | +5 / -5 |
| `NotificationWorker` | 60 min | Heartbeat e alertas externos | +10 / -5 |
| `SyncWorker` | 4h | Sincroniza acervo físico com o banco de dados | +10 / -5 |
| `PlaylistWorker` | Diário 00:00 | Gera grade de 24h com regras de mood/gênero | +20 / -10 |
| `DownloaderWorker` | Diário 01:00 | Aquisição proativa de faixas durante a madrugada | +15 / -8 |
| `DailyReportWorker` | Diário 18:00 | Relatório gerencial do dia (CSV + JSON) | +20 / -10 |
| `ReportWorker` | Semanal | Exporta CSV com faixas mais tocadas | +20 / -10 |

### 4.1 Ciclo de Vida de um Worker

```
WorkerManager.run_cycle(name)
    → log INFO "[Worker] ▶ CICLO INICIADO"
    → broadcast WebSocket: {type: "worker_event", status: "running"}
    → worker.execute_cycle()          ← WorkerBase
        → worker.run_cycle()          ← lógica de negócio
        → reward_store.record(score)
    → log INFO "[Worker] ✓/⚠/✗ CICLO CONCLUÍDO | metadata detalhado"
    → broadcast WebSocket: {mensagem humana, score, violations, metadata}
    → _cycle_history.append(...)      ← usado pelo DailyReportWorker
```

---

## 5. Fluxo de Comunicação e Telemetria

### 5.1 API → Dashboard (Real-time)

1. O **Dashboard (Vite/React)** estabelece conexão **WebSocket (`/ws/status`)**.
2. O servidor envia heartbeats a cada 30 segundos para manter o túnel TCP aberto.
3. Ciclo de evento:
   - Um **Worker** finaliza sua tarefa no `worker_manager.py`.
   - `run_cycle` invoca `api.manager.broadcast_event`.
   - O evento (status, score, metadata, mensagem legível) é transmitido via WebSocket.
   - A UI reage instantaneamente exibindo o log descritivo.

### 5.2 Logs de Sistema

- Backend centraliza logs em `logs/omni_system.log` e logs diários datados.
- Log primário: `D:\RADIO\LOG ZARARADIO\omni_system.log`.
- Endpoint de tailing remoto: `GET /api/status/logs/system` (últimas 50 linhas).

### 5.3 Controle (Frontend → API)

1. Requisições RESTful para controle de workers e configurações.
2. Persistência via `SessionLocal` (thread-safe scoping).
3. Mudanças de estado refletidas no próximo ciclo do worker.

---

## 6. Fluxo de Inicialização

```
START_OMNI.bat
    └── start /B pythonw main.py     ← sem janela de console
            └── main.py
                    ├── --headless → orchestrator.run_headless()
                    └── (padrão)  → core/launcher.run_app()
                            ├── orchestrator.bootstrap()   (admin, mutex, wake lock)
                            ├── orchestrator.start_core()  (API, workers, scheduler)
                            ├── tk.Tk() → withdraw()       (oculto imediatamente)
                            ├── start_tray_icon()          (thread daemon)
                            └── webbrowser.open(8001)      (quando API pronta)
```

### 6.1 Estratégia de Ocultação

- `START_OMNI.bat`: usa `pythonw` + `start /B` — nenhuma janela de CMD ou console.
- `core/launcher.py`: `root.withdraw()` chamado **antes** de qualquer `after()` — janela Tkinter nunca visível.
- Subprocessos internos (FFmpeg, API): disparados com flag `CREATE_NO_WINDOW` no Windows.
- Único elemento visual: ícone na bandeja do sistema (System Tray).

---

## 7. Arquivos e Diretórios Críticos

| Caminho | Descrição |
|---------|-----------|
| `main.py` | Entry point; detecta `--headless` |
| `START_OMNI.bat` | Launcher Windows |
| `core/launcher.py` | Inicialização da GUI oculta e tray |
| `worker_manager.py` | Orquestrador de workers e scheduler |
| `workers/` | Um `.py` por worker |
| `api/manager.py` | FastAPI app + WebSocket broadcast |
| `director/orchestrator.py` | Bootstrap e sequência de inicialização |
| `core/reward.py` | RewardStore — persistência de scores |
| `config/settings.json` | Configurações de paths e intervalos |
| `core/radio_omni.db` | SQLite com acervo musical |
| `D:\RADIO\LOG ZARARADIO\omni_system.log` | Log principal |
| `D:\RADIO\MUSICAS\` | Acervo de faixas |
| `D:\RADIO\PROGRAMACAO\` | Grades geradas pelo PlaylistWorker |
| `D:\RADIO\VINHETAS\` | Vinhetas para a grade |
| `D:\RADIO\SPOTS\` | Spots publicitários |
| `D:\SERVIDOR\BOLETINS\` | Boletins sincronizados do GDrive |
| `reports/` | Relatórios CSV/JSON dos workers |

---

## 8. Integrações Externas

| Sistema | Endereço | Protocolo | Status |
|---------|---------|-----------|--------|
| vMix | `172.16.217.226:8088` | HTTP | ✅ Ativo |
| ZaraRadio | `D:\ZaraRadio\ZaraRadio.exe` | Processo Windows | ✅ Monitorado |
| BUTT (encoder) | Processo Windows | pywinauto | ✅ Monitorado |
| Google Drive | API REST | OAuth2 | ✅ Ativo |
| WeatherAPI | API REST | HTTP | ✅ Ativo (Natal/RN) |
| Z-API / Evolution (WhatsApp) | Webhook | HTTP | 🕒 Pendente |

---

## 8.1 Regras de Segurança Acústica (NÃO NEGOCIÁVEIS)

Estas regras são impostas explicitamente e **não devem ser violadas por nenhuma refatoração**:

1. **ZaraRadio nunca altera o dispositivo de áudio.** O ZaraRadio roda com a placa de saída fixa; o OmniCore não repassa nem altera essa configuração.
2. **O sistema NUNCA modifica volume automaticamente.** Nenhum módulo de monitoramento/autopilot (`core/monitor.py`, `scripts/audio_manager.py`) chama `SetMasterVolume` / `SetVolume`. O `AudioManager` (`scripts/audio_manager.py`) é **estritamente somente-leitura** (mede pico/dB via `IAudioMeterInformation`), e serve apenas para exibir telemetria no dashboard (VU meter, dB).
3. **Controle de volume é AÇÃO MANUAL EXPLÍCITA** do operador, via comando ntfy `volume NN%` (ex.: `volume 80`). Esse comando é tratado em `services/ntfy_listener_service.py` → `scripts/volume_control.py`, que aplica o volume **apenas** na placa de transmissão (`INTERNO (2- USB Audio CODEC)` / `USB Audio CODEC`) e **nunca** é chamado pelo monitor automático. Qualquer mudança automática de volume é considerada bug crítico.

> **Histórico de correção:** em 2026-08, o `audio_manager.py` continha `limit_app_volume()` que chamava `SetMasterVolume` em ZaraRadio.exe/NDI Monitor.exe — violando a regra 2. O método foi **removido** e `core/monitor.py` teve as 5 chamadas a `limit_app_volume` eliminadas, substituídas por aviso de log somente-leitura (`check_volume_safety`).

---

## 9. Bugs Corrigidos — Epic 2026-05-22

### BUG-01 — NameError derrubava o scheduler inteiro
**Arquivo:** `worker_manager.py` — job #14 (playlist maintenance)  
**Causa:** `playlist_engine_instance` referenciado sem import → `NameError` na inicialização do APScheduler → todos os 14 jobs paravam silenciosamente.  
**Sintoma:** Relatório diário zerado; workers aparentemente inativos.  
**Fix:** Import tardio e protegido dentro do job com `try/except`.

### BUG-02 — Janela Python visível no desktop
**Arquivos:** `START_OMNI.bat`, `core/launcher.py`  
**Causa:** `.bat` usava `python.exe`; `launcher.py` chamava `root.after(1000, root.withdraw)` criando flash de 1s.  
**Fix:** `.bat` usa `pythonw` + `start /B`; `launcher.py` chama `root.withdraw()` imediatamente após `tk.Tk()`.

### BUG-03 — Logs vagos no frontend
**Arquivo:** `worker_manager.py`  
**Causa:** `run_cycle()` não emitia eventos WebSocket; frontend recebia apenas `{status, score}` sem contexto.  
**Fix:** Broadcast rico por worker com mensagem legível, violations, metadata e timestamp. Imports de workers isolados — falha de um não derruba os demais.

---

## 10. Procedimentos de Diagnóstico

```powershell
# Log em tempo real
Get-Content "D:\RADIO\LOG ZARARADIO\omni_system.log" -Tail 50 -Wait

# Status dos workers via API
curl http://localhost:8001/api/workers
curl http://localhost:8001/api/status

# Swagger completo
# http://localhost:8001/docs

# Verificar porta da API
netstat -ano | findstr :8001

# Testar conectividade vMix
Test-NetConnection 172.16.217.226 -Port 8088

# Diagnóstico com console visível
python main.py
```

---

## 11. Pendências e Roadmap

| Item | Prioridade | Status |
|------|-----------|--------|
| Notificações WhatsApp (Z-API/Evolution) | P1 | 🕒 Aguarda endpoint |
| `crash.log` dedicado para erros de pré-inicialização | P1 | 🕒 Não implementado |
| Métricas avançadas Librosa (danceability, valence) | P2 | 🕒 Em fila |
| Motor de playlisting com clima em tempo real | P2 | 🕒 Em fila |
| Testes automatizados com cobertura de workers | P2 | 🕒 Em fila |

---

## 12. Bugs Corrigidos — Epic 2026-08-04

### BUG-04 — Spider não puxava boletins/jornais (caminho morto)
**Arquivo:** `scripts/omni_spider.py`  \n**Causa:** `drive_base` estava hardcoded como `H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026`, unidade que **não existe** nesta máquina → todos os 5 alvos falhavam com "Fonte não encontrada" → `updated_total: 0`.  \n**Fix:** `OmniSpider._load_drive_base()` agora lê `grade.pasta_drive_boletins` de `config/settings.json` e sobe um nível até `00_PRODUCAO_2026` (fallback para o caminho real do servidor).  \n**Extra:** `_sync_daily_single` (NJUD) foi corrigido para copiar o jornal mais recente para um arquivo **plano** `JORNAL_NJUD.mp3` no destino (antes criava subpastas `SEGUNDA/TERCA/...` erradas).  \n**Verificação:** execução direta retornou `updated_total: 56` (49 boletins, 5 NJUD, Giro #104, Levemente #111).

### BUG-05 — Repetição de artista na playlist (clean_artist_name quebrado)
**Arquivo:** `scripts/artist_cleaner.py` (regra de não-repetição já existia em `director/grade_rules.py` → `GestorFila.historico_artistas`).  \n**Causa:** o cleaner antigo retornava o **título inteiro** da música como "artista" (ex.: `Camaroes - Orquestra Guitarrística - Espionagem Industrial` → a string toda). Cada faixa virava um "artista" único → a regra de histórico nunca registrava o artista real → repetições dentro do bloco.  \n**Fix:** `clean_artist_name` reescrito para extrair o **ARTISTA** (primeira parte antes de ` - `), normalizar caixa/acentos/pontuação e limpar sufixos de edição. A regra de não-repetição existente (janela de 30 artistas / 80 músicas, cross-bloco) agora funciona de fato.  \n**Teste:** `tests/test_grade_rules.py::test_montar_bloco_sem_repeticao_de_artista` (com isolamento do `engine_history.json` em setUp/tearDown).

### BUG-06 — flicker de status do BUTT (verde/amarelo oscilando)
**Arquivo:** `routers/status.py` (`analisar_instancias_butt`).  \n**Causa:** o status usava CPU do processo (`cpu > 0.5`) como critério, e o BUTT idle oscila CPU ~0 → flip entre "transmitindo" e "conectado (ocioso?)".  \n**Fix:** status agora é **estável** — `ESTABLISHED` (socket TCP para o Icecast) = `transmitindo`; sem conexão = `parado`. CPU removida do critério. Adicionado `connected`/`db` reais (pico da placa USB via `audio_manager.get_master_peak`) ao payload para o VU meter do dashboard.

### BUG-07 — Violação da regra de segurança acústica (volume modificado pelo sistema)
**Arquivos:** `scripts/audio_manager.py`, `core/monitor.py`.  \n**Causa:** `audio_manager.limit_app_volume()` chamava `SetMasterVolume` em ZaraRadio.exe/NDI Monitor.exe, invocado 5× em `core/monitor.py`.  \n**Fix:** `limit_app_volume` **removido**; `AudioManager` é agora estritamente somente-leitura; chamadas em `monitor.py` substituídas por aviso de log. Veja §8.1.  \n**Complemento:** comando manual `volume NN%` via ntfy implementado em `scripts/volume_control.py` (ação explícita do operador, só na placa `INTERNO / USB Audio CODEC`).

---

*Documentação mestre — Pickle Rick. Wubba Lubba Dub Dub! 🥒*  \
*Atualizar ao término de cada Epic.*
