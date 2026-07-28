# Análise e Plano de Melhorias — `radio_manager_agent` (Omni Core V2)

> Análise feita com base no clone real do repositório (branch `main`), não apenas no README.
> Data da análise: 21/07/2026

---

## 1. Visão geral do sistema

O Omni Core V2 é um sistema de automação de rádio em **Python (79,9%) + React (16,1%) + CSS**, dividido em:

- **Core**: banco SQLite via SQLAlchemy, config loader, launcher, scheduler.
- **Workers**: ~17 agentes autônomos (Guardian, Curadoria, Sync, Report, Bulletin, Downloader, Njud, Notification, etc.) agendados via APScheduler.
- **Director**: motor de programação musical com auditoria de regras, actor-critic e playlist engine.
- **API**: FastAPI expondo endpoints para o frontend.
- **Frontend**: dashboard React (Vite).

O projeto é **funcional, ambicioso e bem documentado** (muitos `.md` explicando decisões, tickets, roadmap). Isso já é um diferencial positivo — poucos projetos desse porte têm tanta documentação de processo. Mas a base de código tem sinais claros de **crescimento orgânico rápido** (provavelmente com apoio de IA generativa), sem processos de engenharia que normalmente acompanham esse crescimento.

---

## 2. Pontos fortes (o que já está bem feito)

- **Separação em camadas** (core / workers / director / api / routers / services / scripts) é uma arquitetura sensata para o domínio.
- **`config_loader.py`** é exemplar: um único ponto de carregamento, resolve `${VAR}` a partir do `.env`, não expõe segredos em log, tem cache e `reload_settings()`.
- **`.env.example`** + `.gitignore` corretos: nenhum segredo real foi encontrado versionado (busquei por chaves de API hardcoded — nada encontrado).
- **Whitelist explícita de colunas** em `init_db()` (comentário no código: *"nunca interpolar input externo em DDL"*) — mostra consciência de segurança contra SQL injection nesse ponto específico.
- **52 funções de teste** distribuídas em 19 arquivos (`tests/`), cobrindo curadoria, actor-critic, circuit breaker, quarentena, sazonalidade — cobertura conceitual ampla, mesmo que não medida via `pytest --cov`.
- Documentação de processo rica (`MODULARIZATION_ROADMAP.md`, `TICKETS_RESUMO.md`, `PLANO_ENGENHARIA_V1.md`) indica que a equipe já pensa em dívida técnica — este plano complementa esse esforço.

---

## 3. Problemas identificados

### 3.1 Arquitetura e acoplamento

| Problema | Onde | Impacto |
|---|---|---|
| **Lógica de negócio (grade de programação da rádio) hardcoded dentro da camada de banco de dados** | `core/database.py`, função `init_db()` — dezenas de linhas de JSON com horários, pastas e programas fixos | Viola separação de responsabilidades. Qualquer mudança na grade exige editar código Python e redeploy, quando deveria ser dado de configuração/seed. |
| **Mistura de SQLAlchemy com `sqlite3` cru no mesmo arquivo** | `core/database.py` | Duas formas de acessar o mesmo banco aumenta risco de locks, inconsistência de transação e dificulta migrar de SQLite no futuro. |
| **Migrações de schema via `ALTER TABLE` manual em `try/except`** | `core/database.py` | Não há histórico de versão do schema (tipo Alembic). Funciona, mas é frágil e silencioso — erros reais de schema podem ser engolidos pelo `except sqlite3.OperationalError: pass`. |
| **Caminhos absolutos do Windows (`D:\RADIO`, `C:\Users\...`) espalhados no código-fonte** (não só em config) | `core/database.py`, `director/orchestrator.py` (`setup_logging`), 8 arquivos no total | Sistema fica **acoplado à máquina de produção específica**. Dificulta testes, CI, Docker e portabilidade — mesmo sendo um sistema Windows-only por natureza (ZaraRadio/BUTT), isso deveria estar 100% em `config/settings.json`, nunca no código. |
| **`sys.path.insert`/`append` usado ~20 vezes** | vários módulos | Sinal de que o projeto não é instalado como pacote Python (`pip install -e .`) — hack recorrente em vez de estrutura de packaging adequada. |

### 3.2 Tratamento de erros e qualidade de código

| Problema | Extensão | Impacto |
|---|---|---|
| **246 ocorrências de `except Exception`** | todo o projeto | Captura ampla demais quase sempre — mascara bugs reais, dificulta debug. Deveria capturar exceções específicas (`sqlite3.OperationalError`, `requests.RequestException`, etc.). |
| **17 `except:` genéricos (bare except)** | todo o projeto | Pior ainda que o acima — chega a engolir `KeyboardInterrupt`/`SystemExit`. Deve ser eliminado por completo. |
| **Arquivos muito grandes / possivelmente com múltiplas responsabilidades** | `director/grade_rules.py` (653 linhas), `core/monitor.py` (549 linhas), `worker_manager.py` (399 linhas) | Dificulta manutenção, revisão de PR e testes unitários isolados. |
| **`print()` usado em paralelo com `logging`** (20 arquivos fora dos testes) | diversos | Inconsistência — parte do sistema loga corretamente, parte usa `print`, perdendo nível de severidade, timestamp e destino configurável. |

### 3.3 Testes e integração contínua

- **Não há pipeline de CI** (nenhum `.github/workflows`, nenhum `pytest.ini`/`pyproject.toml` com config de teste). Os 52 testes existentes só rodam se alguém lembrar de rodar `pytest` manualmente antes de mergear — ou seja, **nada impede código quebrado de ir para produção**.
- Não há medição de cobertura (`coverage.py`), então não se sabe quanto do sistema (principalmente `workers/` e `services/`) está de fato coberto.
- Testes de integração (`test_integration_system.py`, `test_startup.py`) dependem de ambiente Windows real (paths, processos como ZaraRadio/BUTT). **Decisão confirmada do time: o sistema vai continuar dependendo do ambiente real de produção — não faz sentido mockar ZaraRadio/BUTT/vMix.** Isso é uma restrição de domínio legítima (são automações de hardware/software de terceiros que não têm API de simulação confiável), então a estratégia de CI precisa ser desenhada em torno disso, não contra isso.

> **Estratégia de CI ajustada — runner self-hosted, sem mocks:**
> Em vez de um runner genérico na nuvem (que não teria ZaraRadio/BUTT/vMix), a recomendação é instalar um **GitHub Actions self-hosted runner** na própria máquina Windows onde o sistema já roda (produção ou uma máquina gêmea de contingência que a rádio já mantenha como backup). Isso permite rodar os 52 testes existentes — incluindo os de integração — contra o ambiente real de verdade a cada push, sem inventar dados falsos.
> Cuidados necessários para isso não colocar a transmissão ao vivo em risco:
> - Rodar os testes em um **banco SQLite de teste separado** (`radio_omni_test.db`), nunca no banco de produção.
> - Testes que tocam áudio/streaming real devem rodar em **janela de baixo tráfego** (ex.: madrugada) ou apontar para uma pasta de acervo de teste, não a pasta ao vivo.
> - Runner configurado para **não ter permissão de reiniciar/matar processos de produção** (ZaraRadio, BUTT) durante o job — só observar/validar.
> - Se houver uma máquina de contingência/backup com o mesmo software instalado, ela é a candidata ideal para o runner — testa contra o sistema real sem tocar na transmissão principal.

### 3.4 Higiene do repositório

- **Artefatos gerados em runtime foram commitados**, contrariando o próprio `.gitignore` do projeto:
  - `logs/omni_system.log`, `logs/ffmpeg_relay.log` (52 KB), `logs/radio_agent_20260511.log`, `logs/engine_history.json`
  - `reports/Worker_Audit_20260513.csv` (76 KB), `reports/*.md`
  - Um desses logs revelou um **caminho local com nome de usuário do computador de produção** (`C:\Users\STREAMING\...`) — vazamento de informação de infraestrutura, mesmo que de baixo risco.
- Isso incha o histórico do Git ao longo do tempo e gera diffs de "ruído" a cada execução se alguém commitar de novo por engano.
- README do projeto tem uma assinatura estilizada de personagem fictício ("Desenvolvido com Malícia e Competência por Pickle Rick") — inofensivo, mas destoa de um projeto usado por uma instituição (rádio de tribunal, aparentemente TJRN, a julgar pelos caminhos `RADIO TJRN CONTEÚDO`). Vale avaliar se é a imagem que a instituição quer publicamente.

### 3.5 Segurança (pontos menores, mas a verificar)

- Nenhum segredo hardcoded encontrado — **positivo**.
- IP de rede interna do vMix aparece como exemplo no `.env.example` (`172.16.217.226`) — não é segredo crítico, mas idealmente exemplos usam IPs de documentação (`192.0.2.x` / `10.0.0.x` genéricos) para não vazar topologia real da rede da instituição.
- Sem `SECURITY.md` ou processo definido para reportar vulnerabilidades — relevante por rodar em rede de instituição pública.
- API FastAPI: não localizei nesta análise validação/autenticação nos endpoints dos `routers/` — vale confirmar se o dashboard e a API ficam expostos apenas em rede interna (`127.0.0.1`/LAN) ou se há necessidade de autenticação básica, já que comandos de sistema (reboot prevention, workers, downloader) são sensíveis.

### 3.6 Documentação

- Documentação abundante, mas **fragmentada e sem índice único**: `docs/` tem 15 arquivos `.md` com sobreposição de conteúdo (`MUDANCAS.md`, `BEFORE_AFTER_COMPARISON.md`, `MODULARIZATION_ROADMAP.md`, `PLANO_ENGENHARIA_V1.md` parecem contar histórias parcialmente redundantes).
- Falta um `CONTRIBUTING.md` e um `ARCHITECTURE.md` enxuto e atual — a "fonte da verdade" da arquitetura está espalhada em vários relatos históricos.

---

## 4. Plano de ação priorizado

### 🔴 Prioridade Alta (fazer primeiro — baixo esforço, alto retorno)

1. **Configurar CI básico via runner self-hosted** (GitHub Actions instalado na máquina Windows real — produção ou contingência): rodar `pytest` e `ruff`/`flake8` a cada push/PR, contra o ambiente de verdade (ZaraRadio/BUTT/paths reais), usando um banco SQLite de teste isolado. Sem mocks — os testes de integração continuam validando o sistema real, só passam a rodar automaticamente em vez de depender de alguém lembrar.
2. **Remover do Git os artefatos gerados** (`logs/*.log`, `logs/engine_history.json`, `reports/*.csv`, `reports/*.md`) e reforçar o `.gitignore` já existente com `git rm --cached`. Adicionar histórico limpo a partir daqui.
3. **Eliminar os 17 `except:` bare** — trocar por exceções específicas ou, no mínimo, `except Exception as e: logger.exception(...)`.
4. **Extrair a "grade padrão" hardcoded de `core/database.py` para um arquivo de seed/config** (`config/grade_padrao.json`), carregado pelo `config_loader`. Isso tira lógica de negócio da camada de dados.

### 🟡 Prioridade Média (próximas 2-4 semanas)

5. **Adotar Alembic para migrações** em vez de `ALTER TABLE` manual — dá versionamento e rollback de schema.
6. **Padronizar logging**: substituir todos os `print()` remanescentes por `logger`, garantindo nível (`DEBUG/INFO/WARNING/ERROR`) e formato consistentes.
7. **Reduzir uso de `except Exception` genérico**: priorizar os módulos críticos primeiro — `core/database.py`, `worker_manager.py`, `director/orchestrator.py`.
8. **Quebrar arquivos grandes** (`grade_rules.py`, `monitor.py`, `worker_manager.py`) em submódulos por responsabilidade (ex.: `grade_rules/validators.py`, `grade_rules/policies.py`).
9. **Centralizar todos os caminhos do sistema de arquivos em `config/settings.json`**, removendo os últimos `D:\RADIO` hardcoded do código-fonte (`database.py`, `orchestrator.py`).
10. **Medir cobertura de testes** com `pytest-cov` e definir uma meta mínima (ex.: 60% para começar, subindo com o tempo).
11. **Instalar e configurar o runner self-hosted**: definir se roda na máquina de produção ou numa máquina de contingência com o mesmo software; criar banco `radio_omni_test.db` isolado; agendar jobs de integração completa (que tocam áudio/streaming) para janela de baixo tráfego; restringir permissões do runner para não derrubar processos de produção.

### 🟢 Prioridade Baixa (melhoria contínua / nice-to-have)

12. **Consolidar documentação**: criar `docs/ARCHITECTURE.md` único e atual; mover relatos históricos (`BEFORE_AFTER_COMPARISON.md`, `MUDANCAS.md`) para uma pasta `docs/historico/`.
13. **Adicionar `CONTRIBUTING.md`** com padrão de commits, como rodar testes localmente e convenção de branches.
14. **Empacotar o projeto adequadamente** (`pyproject.toml` com `[project]` + instalação editável), eliminando os `sys.path.insert` manuais.
15. **Revisar segurança de rede da API/dashboard**: confirmar exposição apenas em rede interna ou adicionar autenticação mínima nos endpoints sensíveis (reboot, workers, downloader).
16. **Sanitizar exemplos de config** (`.env.example`, `settings.example.json`) trocando IPs/caminhos reais por exemplos genéricos.
17. Revisar tom do README para produção institucional (assinatura "Pickle Rick") — decisão de produto/comunicação, não técnica.

---

## 5. Status das melhorias aplicadas (28/07/2026)

As seguintes melhorias foram implementadas e verificadas em execução real do sistema:

### ✅ Concluídas

| # | Melhoria | Arquivo(s) | Status |
|---|---|---|---|
| — | Dados falsos do MOCKUP 2 substituídos por dados reais (psutil, API) | `frontend/src/App.jsx`, `routers/status.py` | ✅ |
| — | ControlPanel restaurado com comandos reais (Gera 24h, Sync Acervo, Spider) | `frontend/src/App.jsx` | ✅ |
| — | VU Meter, métricas de áudio e rede agora refletem dados reais do WebSocket/API | `frontend/src/App.jsx`, `WebSocketContext.jsx` | ✅ |
| — | `streaming_stats.py` sem hardcode fictício — lê de `config/settings.json` | `scripts/streaming_stats.py` | ✅ |
| — | `engine.py` sem "Configuração fictícia de streaming" | `routers/engine.py` | ✅ |
| — | Endpoint `GET /hardware/realtime` com uptime real, disco, CPU, RAM, temperatura | `routers/status.py` | ✅ |
| — | NtfyListener com normalização de texto (sem acentos, case-insensitive), matching tolerante e anti-loop reforçado | `services/ntfy_listener_service.py` | ✅ |
| — | `core/monitor.py`: import corrigido (`from typing import Optional`) | `core/monitor.py` | ✅ |
| — | Frontend rebuildado (`npm run build`) — dist atualizado | `frontend/dist/` | ✅ |

### 📊 Métricas do sistema em execução
- Processo `main.py`: **rodando** (GuardianWorker ciclo a cada 2s, ApiWorker a cada 30s)
- API health check: **OK** (porta 8001, score=10, sem violations)
- Frontend dist: rebuildado com sucesso (31 modules, 279.92 kB JS)
- Nenhuma dependência faltando após instalação de `pywinauto`, `pycaw`, `google-genai`, `yt-dlp`

### ⏳ Ainda pendentes (do plano original)
- Prioridade Alta: CI runner self-hosted, bare excepts, grade hardcoded extraída
- Prioridade Média: Alembic, logging padronizado, quebrar arquivos grandes, cobertura
- Prioridade Baixa: docs consolidação, CONTRIBUTING.md, packaging, segurança da API

```
Semana 1-2   ── CI via runner self-hosted (máquina real) + limpeza de artefatos versionados + bare excepts
Semana 3-4   ── Extrair grade hardcoded + padronizar logging + Alembic
Mês 2        ── Setup completo do runner (banco de teste isolado, janela de baixo tráfego) + refatorar
                arquivos grandes + cobertura de testes + packaging
Mês 3+       ── Consolidação de docs + revisão de segurança da API + polimento
```

---

## 6. Observação final

Nada aqui indica um projeto malfeito — é um sistema real, em produção, resolvendo um problema complexo (automação de rádio + curadoria musical com IA + integração com múltiplos sistemas de terceiros como ZaraRadio, BUTT e vMix). Os problemas listados são **típicos de um projeto que cresceu rápido**, provavelmente com forte apoio de geração de código assistida, sem ainda ter passado por um ciclo de "endurecimento" (hardening) de engenharia. O plano acima ataca primeiro os itens que reduzem risco de quebra em produção (CI, exceções, limpeza de repo) antes de partir para refatorações estruturais maiores.

Importante: a estratégia de testes foi desenhada respeitando a decisão do time de manter dependência do ambiente real (ZaraRadio/BUTT/vMix) — não há proposta de substituir isso por simulação. O ganho de automação vem de rodar os testes já existentes de forma consistente via runner self-hosted, com as salvaguardas descritas na seção 3.3, e não de recriar o comportamento desses sistemas artificialmente.
