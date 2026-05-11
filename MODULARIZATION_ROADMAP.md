# Roadmap de Modularização e Deploy do Backend

Este documento descreve a implementação do backend modular do Omni Core V2, incluindo a infraestrutura de workers, o orquestrador, o processo de build em EXE e a atualização automática do sistema.

## 1. Estrutura criada nesta primeira fase

- `core/worker_base.py`
  - base abstrata de worker
  - resultado padronizado com score, status, violações e metadata
- `core/reward.py`
  - store de recompensas persistente em JSON
  - histórico de ciclos e resumo por worker
- `workers/playlist_worker.py`
  - worker para geração de playlists diárias
  - usa `playlist_engine_instance` para montar blocos
- `workers/audit_worker.py`
  - worker de auditoria para validação de playlists
  - registra falhas em arquivos `.m3u`
- `worker_manager.py`
  - registra workers
  - executa ciclos individuais ou todos os workers
  - mantém store de recompensas comum
  - agenda workers via APScheduler
- `core/launcher.py`
  - inicialização simplificada do app
  - garante instância única e privilégios de admin
  - inicia API e UI sem bloquear
- `api/manager.py`
  - configura FastAPI e routers
  - inicia orquestrador no startup

## 2. Passos documentados por implementação

1. Criar a camada de infraestrutura comum para workers
   - Base `WorkerBase`
   - Resultado padrão `WorkerResult`
   - Reward store persistente

2. Construir os primeiros workers
   - `PlaylistWorker` para geração de bloco
   - `AuditWorker` para validação de arquivos `.m3u`

3. Criar o gerenciador que injeta a mesma store de recompensas
   - uso de `execute_cycle()` para gravar score automaticamente
   - visão centralizada de health e resultados

4. Integrar o orquestrador com APScheduler
   - agendamento de playlists diárias
   - execução periódica de workers de curadoria, sync, weather, audit e butt

5. Simplificar startup e UI
   - evitar abertura automática de navegador
   - manter janela oculta até acionamento manual
   - reduzir as verificações em série no processo de inicialização

## 3. Build e atualização automática

### 3.1 Arquivos de suporte
- `build.py`
  - gera `dist/omni_core.exe` usando PyInstaller
  - adiciona recursos e configurações necessárias
  - cria arquivos auxiliares: `VERSION`, `omni_core.md5` e `code.md5`
- `deploy.py`
  - instala a aplicação em `C:\Program Files\OmniCore`
  - configura auto-início via pasta Startup
  - registra aplicação no Windows
- `workers/update_worker.py`
  - verifica mudanças no código a cada 1 hora
  - reconstrói o executável automaticamente quando necessário
  - registra eventos e notifica via Telegram

### 3.2 Fluxo de build

1. `python build.py`
   - limpa `build/` e `dist/`
   - executa PyInstaller
   - gera executável standalone

2. `dist/omni_core.exe` é produzido
3. `dist/VERSION`, `dist/omni_core.md5` e `dist/code.md5` são criados
4. o EXE pode ser distribuído manualmente ou instalado via `deploy.py`

### 3.3 Fluxo de atualização automática

1. `UpdateWorker` roda periodicamente
2. calcula hash MD5 do código-fonte
3. compara com `dist/code.md5`
4. se diferente, dispara `build.py`
5. reconstrói `omni_core.exe`
6. atualiza o hash no `dist/code.md5`
7. envia notificação de atualização

### 3.4 Configuração do UpdateWorker

Em `config/settings.json`:

```json
{
  "workers": {
    "UpdateWorker": {
      "interval_hours": 1
    }
  }
}
```

## 4. Estrutura de distribuição esperada

```
dist/
├── omni_core.exe          # Executável principal
├── VERSION                # Versão atual do build
├── omni_core.md5          # Hash do executável
└── code.md5               # Hash do código-fonte
```

## 5. Deploy e instalação

### Primeiro deploy

1. Executar `python deploy.py` como administrador
2. O script:
   - garante PyInstaller instalado
   - compila o EXE
   - copia arquivos para `C:\Program Files\OmniCore`
   - configura execução automática via Startup
   - registra a aplicação no Windows

### Uso diário

- iniciar `C:\Program Files\OmniCore\omni_core.exe`
- se houver atualização no código, o `UpdateWorker` reconstruirá o EXE
- a próxima reinicialização usará a versão atualizada

## 6. Monitoramento e logs

- Logs de runtime: `D:\RADIO\LOG ZARARADIO\omni_system.log`
- Eventos de worker estão disponíveis no dashboard `http://localhost:8001`
- Mensagens importantes:
  - `🔄 Mudanças detectadas no código`
  - `🔨 Reconstruindo EXE...`
  - `✅ Sistema atualizado com sucesso!`

## 7. Próximas fases recomendadas

### Fase 2 — Estruturação dos workers principais

- `ActorCriticWorker`
- `CuradoriaWorker`
- `GuardianWorker`
- `DownloaderWorker`
- `SyncWorker`
- `WeatherWorker`
- `ApiWorker`

### Fase 3 — Integração com o orquestrador

- `worker_manager.py` em execução contínua
- agenda de ciclos via `APScheduler`
- endpoint de health e status de workers

### Fase 4 — Refactor do backend existente

- migrar lógica de `main.py` para `orchestrator.py`
- reduzir dependências de UI desktop (`Tkinter`, `pystray`)
- separar frontend estático da API
- deixar routers como binding temporário até `ApiWorker`

## 8. Critérios de aceitação

- workers independentes e testáveis
- store de recompensas persistente
- `worker_manager.py` executa ciclos agendados e retorna payload padronizado
- build de `omni_core.exe` reproduzível com `build.py`
- atualização automática detecta e reconstrói o EXE
- documentação completa disponível para continuidade do desenvolvimento
