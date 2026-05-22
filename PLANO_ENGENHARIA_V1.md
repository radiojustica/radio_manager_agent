# Plano de Engenharia — Omni Core V2
**Versão:** 1.0  
**Data:** 2026-05-22  
**Escopo:** Hardening de segurança, qualidade de código e sustentabilidade operacional  
**Baseado em:** Scan estático Amazon Q (182 findings) + análise de arquitetura

---

## 1. Contexto e Diagnóstico

O Omni Core V2 é um sistema de automação de rádio em produção contínua (24/7) rodando em Windows. A análise revelou que o sistema **funciona**, mas carrega dívida técnica acumulada que representa risco operacional real:

- **14 workers** orquestrados por APScheduler sem circuit breaker
- **Credenciais em texto plano** no repositório (`config/gdrive_api_key.txt`, `config/settings.json`)
- **Tratamento de erros silencioso** (`except: pass`) em ~40 pontos — falhas são engolidas sem registro
- **Chamadas ao Gemini AI** sem rate limiting — risco de custo descontrolado
- **SQL construído por string formatting** em `core/database.py`
- **subprocess com `shell=True`** em `core/monitor.py` — vetor de injeção de comandos
- **Arquivos XML** parseados sem proteção XXE em `scripts/vmix_controller.py`

O sistema não tem risco de colapso imediato, mas qualquer incidente em produção será difícil de diagnosticar e corrigir com a estrutura atual.

---

## 2. Objetivos

| # | Objetivo | Métrica de Sucesso |
|---|---|---|
| 1 | Eliminar exposição de credenciais | Zero secrets em arquivos versionados |
| 2 | Tornar falhas visíveis | Zero `except: pass` sem logging |
| 3 | Proteger contra injeção (SQL, OS, Path) | Findings críticos zerados no próximo scan |
| 4 | Controlar consumo da API Gemini | Rate limiter implementado e testado |
| 5 | Reduzir complexidade dos arquivos grandes | Nenhum arquivo acima de 400 LOC |

---

## 3. Fases e Sprints

### FASE 1 — Segurança Crítica (Semana 1)
> Bloqueadores que precisam ser resolvidos antes de qualquer outra coisa.

---

#### Sprint 1.1 — Gestão de Segredos
**Duração:** 1 dia  
**Arquivos afetados:** `config/`, `.gitignore`, `core/monitor.py`, `worker_manager.py`

**Tarefas:**

1. Criar arquivo `.env` na raiz com todas as chaves sensíveis:
   ```
   GDRIVE_API_KEY=...
   GEMINI_API_KEY=...
   TELEGRAM_BOT_TOKEN=...
   EMAIL_PASSWORD=...
   VMIX_IP=...
   ```

2. Instalar `python-dotenv` e adicionar ao `requirements.txt`

3. Criar `core/config_loader.py` — ponto único de leitura de configuração que mescla `.env` com `settings.json`

4. Remover `config/gdrive_api_key.txt` do repositório e adicionar ao `.gitignore`:
   ```
   .env
   config/gdrive_api_key.txt
   config/settings.json
   *.db
   ```

5. Criar `config/settings.example.json` com valores placeholder para documentar a estrutura

**Critério de aceite:** `git grep -r "AIza\|password\|token"` retorna zero resultados em arquivos versionados.

---

#### Sprint 1.2 — Injeção de Comandos OS
**Duração:** 1 dia  
**Arquivos afetados:** `core/monitor.py`, `services/guardian_service.py`, `worker_manager.py`, `scripts/reboot_blocker.py`

**Problema central:** `subprocess.run("taskkill /F /IM ZaraRadio.exe", shell=True)` — qualquer dado externo que chegue nessa string pode executar comandos arbitrários.

**Tarefas:**

1. Substituir todas as chamadas `shell=True` por listas de argumentos:
   ```python
   # ANTES
   subprocess.run("taskkill /F /IM ZaraRadio.exe /T", shell=True)
   
   # DEPOIS
   subprocess.run(["taskkill", "/F", "/IM", "ZaraRadio.exe", "/T"], 
                  capture_output=True, timeout=10)
   ```

2. Substituir `shell=True` em `schtasks` em `core/monitor.py` (método `manage_tasks`):
   ```python
   # ANTES
   subprocess.run(f'schtasks /Query /TN "{task}"', shell=True, ...)
   
   # DEPOIS
   subprocess.run(["schtasks", "/Query", "/TN", task, "/FO", "LIST"],
                  capture_output=True, encoding="cp1252", timeout=15)
   ```

3. Validar que `executable_path` lido de `settings.json` existe antes de passar ao `Popen`:
   ```python
   from pathlib import Path
   exe = Path(settings["apps"]["zararadio"]["executable_path"])
   if not exe.exists():
       raise FileNotFoundError(f"Executável não encontrado: {exe}")
   subprocess.Popen([str(exe), str(playlist)])
   ```

**Critério de aceite:** `grep -r "shell=True"` retorna zero resultados.

---

#### Sprint 1.3 — SQL Injection e Path Traversal
**Duração:** 1 dia  
**Arquivos afetados:** `core/database.py`, `routers/config.py`, `routers/reports.py`, `director/grade_rules.py`

**Tarefas:**

1. Em `core/database.py` — substituir `cursor.execute(f"ALTER TABLE...")` por query parametrizada:
   ```python
   # A migração manual com f-string é o único ponto de SQL injection real aqui
   # Validar nome da coluna contra whitelist antes de executar
   ALLOWED_COLUMNS = {"mood", "bpm", "valence", "danceability", "quarantine_reason"}
   for nome_col, tipo_col in colunas:
       if nome_col not in ALLOWED_COLUMNS:
           continue
       cursor.execute(f"ALTER TABLE musicas ADD COLUMN {nome_col} {tipo_col}")
   ```

2. Criar utilitário `core/path_utils.py` com função `safe_path(base_dir, user_input)`:
   ```python
   from pathlib import Path
   
   def safe_path(base_dir: Path, user_input: str) -> Path:
       resolved = (base_dir / user_input).resolve()
       if not str(resolved).startswith(str(base_dir.resolve())):
           raise ValueError(f"Path traversal detectado: {user_input}")
       return resolved
   ```

3. Aplicar `safe_path` em todos os pontos onde caminhos são construídos a partir de dados externos (routers, scripts de relatório)

**Critério de aceite:** Findings de `sql-injection` e `path-traversal` zerados no próximo scan.

---

#### Sprint 1.4 — XXE e XML Inseguro
**Duração:** 0,5 dia  
**Arquivos afetados:** `scripts/vmix_controller.py`, `scripts/streaming_stats.py`

**Tarefas:**

1. Substituir `xml.etree.ElementTree` por `defusedxml`:
   ```python
   # requirements.txt: adicionar defusedxml>=0.7.1
   
   # ANTES
   import xml.etree.ElementTree as ET
   tree = ET.parse(response.text)
   
   # DEPOIS
   import defusedxml.ElementTree as ET
   tree = ET.fromstring(response.content)
   ```

**Critério de aceite:** Zero findings `xxe-external-entity` e `denylist-xml-bad-ElementTree`.

---

### FASE 2 — Confiabilidade e Observabilidade (Semana 2)
> Tornar o sistema diagnosticável em produção.

---

#### Sprint 2.1 — Tratamento de Erros
**Duração:** 2 dias  
**Arquivos afetados:** Todos os workers, `api/manager.py`, `gui/console.py`, `director/grade_rules.py`

**Problema:** `except: pass` e `except Exception: continue` mascaram falhas reais. Em um sistema 24/7, isso significa que erros podem acumular silenciosamente por horas.

**Tarefas:**

1. Criar política de tratamento de erros no projeto:
   - `except: pass` → **proibido**
   - `except Exception as e: logger.debug(...)` → permitido apenas para erros esperados e documentados
   - `except Exception as e: logger.error(..., exc_info=True)` → padrão para erros inesperados

2. Varredura e correção arquivo por arquivo (prioridade: workers, depois routers, depois scripts):
   ```python
   # ANTES (padrão encontrado em ~40 locais)
   try:
       resultado = operacao_critica()
   except:
       pass
   
   # DEPOIS
   try:
       resultado = operacao_critica()
   except SpecificException as e:
       logger.warning(f"Operação falhou (esperado): {e}")
   except Exception as e:
       logger.error(f"Falha inesperada em operacao_critica: {e}", exc_info=True)
       raise  # ou retornar estado de erro explícito
   ```

3. Em `services/guardian_service.py`, método `_send_command_to_butt`:
   ```python
   # ANTES
   except: return False
   
   # DEPOIS
   except Exception as e:
       logger.debug(f"Falha ao enviar comando ao BUTT PID {pid}: {e}")
       return False
   ```

**Critério de aceite:** Zero findings `python-try-except-pass` e `python-try-except-continue`.

---

#### Sprint 2.2 — Rate Limiting para Gemini AI
**Duração:** 1 dia  
**Arquivos afetados:** `services/ai_service.py`, `services/gemini_service.py`, `services/curadoria_worker.py`

**Problema:** Chamadas ao Gemini sem controle de frequência. Em caso de loop ou bug, pode gerar custo de centenas de dólares em minutos.

**Tarefas:**

1. Criar `services/rate_limiter.py`:
   ```python
   import time
   import threading
   from collections import deque
   
   class RateLimiter:
       def __init__(self, max_calls: int, period_seconds: float):
           self.max_calls = max_calls
           self.period = period_seconds
           self._calls = deque()
           self._lock = threading.Lock()
       
       def acquire(self) -> bool:
           with self._lock:
               now = time.monotonic()
               # Remove chamadas fora da janela
               while self._calls and now - self._calls[0] > self.period:
                   self._calls.popleft()
               if len(self._calls) >= self.max_calls:
                   return False
               self._calls.append(now)
               return True
       
       def wait_and_acquire(self):
           while not self.acquire():
               time.sleep(0.5)
   ```

2. Aplicar em `services/gemini_service.py`:
   ```python
   from services.rate_limiter import RateLimiter
   
   # Máximo 10 chamadas por minuto (ajustar conforme plano da API)
   _gemini_limiter = RateLimiter(max_calls=10, period_seconds=60)
   
   def call_gemini(prompt: str) -> str:
       _gemini_limiter.wait_and_acquire()
       # ... chamada existente
   ```

3. Adicionar timeout explícito em todas as chamadas HTTP ao Gemini (máximo 30s)

**Critério de aceite:** Findings `python-llm-unbounded-consumption` zerados. Teste manual: 15 chamadas rápidas → as últimas 5 aguardam.

---

#### Sprint 2.3 — Datetime com Timezone
**Duração:** 1 dia  
**Arquivos afetados:** 15+ arquivos (workers, director, routers)

**Problema:** `datetime.now()` sem timezone causa bugs sutis em logs e agendamentos, especialmente em horário de verão.

**Tarefas:**

1. Criar utilitário `core/time_utils.py`:
   ```python
   from datetime import datetime, timezone
   import zoneinfo
   
   TZ_LOCAL = zoneinfo.ZoneInfo("America/Sao_Paulo")
   
   def now_local() -> datetime:
       return datetime.now(tz=TZ_LOCAL)
   
   def now_utc() -> datetime:
       return datetime.now(tz=timezone.utc)
   
   def format_local(dt: datetime = None) -> str:
       if dt is None:
           dt = now_local()
       return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
   ```

2. Substituir todas as ocorrências de `datetime.now()` por `now_local()` ou `now_utc()` conforme contexto

3. Substituir `datetime.now().isoformat()` por `now_utc().isoformat()` em eventos de API (padrão ISO 8601 com timezone)

**Critério de aceite:** Zero findings `python-aware-datetime-with-tzinfo` e `python-naive-datetime-methods`.

---

### FASE 3 — Qualidade e Manutenibilidade (Semana 3)
> Reduzir complexidade para facilitar evolução futura.

---

#### Sprint 3.1 — Refatoração de Arquivos Grandes
**Duração:** 2 dias  
**Arquivos afetados:** `workers/curadoria_worker.py`, `workers/downloader_worker.py`, `worker_manager.py`

**Problema:** Arquivos com alta complexidade ciclomática e LOC excessivo são difíceis de testar e manter.

**Tarefas para `worker_manager.py` (>300 LOC, alta complexidade):**

1. Extrair configuração de schedules para `config/schedules.py`:
   ```python
   SCHEDULES = {
       "GuardianWorker": {"trigger": "interval", "seconds": 30},
       "CuradoriaWorker": {"trigger": "interval", "minutes": 5},
       # ...
   }
   ```

2. Extrair método `start_orchestrator` para `core/orchestrator_setup.py`

3. `WorkerManager` fica responsável apenas por registro e execução de ciclos

**Tarefas para `workers/curadoria_worker.py`:**

1. Separar lógica de análise de áudio em `services/audio_analysis_service.py`
2. Separar lógica de interação com Gemini em chamadas ao `services/ai_service.py` existente

**Critério de aceite:** Nenhum arquivo acima de 400 LOC. Findings de `code-quality-metrics-line-of-code` zerados.

---

#### Sprint 3.2 — Frontend: SSRF e Alert Boxes
**Duração:** 1 dia  
**Arquivos afetados:** `frontend/src/components/AcervoPage.jsx`, `frontend/src/components/ConfigPage.jsx`, `frontend/src/App.jsx`, `frontend/src/components/NowPlayingCard.jsx`

**Tarefas:**

1. Centralizar todas as URLs de API em `frontend/src/api/config.js`:
   ```javascript
   const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';
   export const endpoints = {
     status: `${API_BASE}/status`,
     acervo: `${API_BASE}/acervo`,
     // ...
   };
   ```

2. Substituir `alert()` por componente de notificação React (toast/snackbar):
   ```javascript
   // ANTES
   alert(`Erro: ${error.message}`);
   
   // DEPOIS
   setNotification({ type: 'error', message: error.message });
   ```

3. Validar dados de `JSON.parse` em `NowPlayingCard.jsx` com schema mínimo antes de usar

4. Atualizar dependência vulnerável identificada no `package-lock.json` (`npm audit fix`)

**Critério de aceite:** Zero findings SSRF, alert-box e untrusted-deserialization no frontend.

---

#### Sprint 3.3 — Limpeza Estrutural
**Duração:** 1 dia

**Tarefas:**

1. **Remover duplicação de workers:** `services/curadoria_worker.py` e `workers/curadoria_worker.py` existem em paralelo — consolidar em um único local

2. **Remover arquivos de ticket/planejamento da raiz:** Mover pastas `1a2b3c4d/`, `2d4e5f6a/`, etc. para `docs/tickets/` ou deletar se obsoletos

3. **Substituir variáveis globais em `core/system.py`** por um objeto de estado thread-safe:
   ```python
   # ANTES
   global CURRENT_MOOD
   CURRENT_MOOD = "Ensolarado"
   
   # DEPOIS
   from threading import Lock
   
   class SystemState:
       def __init__(self):
           self._lock = Lock()
           self._mood = "Ensolarado"
       
       @property
       def mood(self) -> str:
           with self._lock:
               return self._mood
       
       @mood.setter
       def mood(self, value: str):
           with self._lock:
               self._mood = value
   
   system_state = SystemState()
   ```

4. **Corrigir `equality-vs-identity`** — substituir `== None` por `is None` e `== True/False` por `is True/False` nos arquivos afetados

**Critério de aceite:** Estrutura de pastas limpa, zero findings `python-assignment-to-global` e `python-equality-vs-identity`.

---

## 4. Backlog Pós-Sprint (Fase 4 — Futuro)

Itens identificados mas fora do escopo imediato:

| Item | Justificativa para adiar |
|---|---|
| Migrar SQLite para PostgreSQL | Requer mudança de infraestrutura, não é bloqueador |
| Internacionalização do frontend (i18n) | Sistema é interno, português é suficiente por ora |
| Containerização (Docker) | Dependências Win32 dificultam containerização |
| CI/CD pipeline | Requer infraestrutura adicional |
| Testes de integração completos | Dependem das refatorações das fases 1-3 |

---

## 5. Dependências e Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Refatoração de `monitor.py` quebrar o Guardian em produção | Alta | Crítico | Testar em ambiente separado antes de deploy; manter backup do arquivo original |
| Rate limiter do Gemini bloquear curadoria legítima | Média | Médio | Configurar limite conservador (10/min) e monitorar logs por 48h |
| Migração de `datetime.now()` causar bug de timezone | Baixa | Médio | Fazer em branch separada, testar agendamentos por 24h |
| Remoção de `shell=True` quebrar comandos `schtasks` | Média | Alto | Testar cada comando individualmente antes do merge |

---

## 6. Ordem de Execução Recomendada

```
Semana 1:  Sprint 1.1 → 1.2 → 1.3 → 1.4  (segurança, não pode esperar)
Semana 2:  Sprint 2.1 → 2.2 → 2.3         (confiabilidade)
Semana 3:  Sprint 3.1 → 3.2 → 3.3         (qualidade)
```

**Regra de ouro:** Cada sprint deve terminar com o sistema funcionando em produção. Nenhuma fase bloqueia a operação da rádio.

---

## 7. Definição de "Pronto" (DoD)

Um sprint está concluído quando:
- [ ] Código implementado e revisado
- [ ] Findings correspondentes zerados no scan Amazon Q
- [ ] Sistema iniciou sem erros (`python start.py`)
- [ ] GuardianWorker reportou ciclo bem-sucedido nos logs
- [ ] Nenhum `except: pass` introduzido no sprint

---

*Documento gerado com base em análise estática (182 findings) e revisão de arquitetura do Omni Core V2.*
