# Registro de Melhorias Aplicadas — OmniCore V2
**Data:** 28/07/2026  
**Sistema:** radio_manager_agent (Omni Core V2 — automação de rádio TJRN)

---

## 1. Problemas Identificados e Corrigidos

### 1.1 Dashboard com Dados Falsos (Mocks)
**Problema:** O MOCKUP 2 do dashboard (`App.jsx`) exibia valores inventados que não refletiam a realidade do sistema:
- Uptime fictício: `04d 12h 30m`
- Qualidade de streaming inventada: `320 kbps AAC`, `10.4 dB`, `14.1 LUFS`
- Bateria do nobreak inventada: `98%`, `Carga 45%`, `Autonomia 2h 15m`
- Temperatura do rack fixa: `22°C`
- Regras de firewall fixas: `145 regras`
- VU Meter com dados gerados por `Math.random()`
- Gráfico SVG estático sem dados reais

**Correção:** Todos os valores falsos foram substituídos por dados reais:
- **Audio:** `player.energy` via WebSocket em tempo real
- **Streaming:** consulta ao Icecast via `/api/engine/stats` + endpoint `/api/status/hardware/realtime` novo
- **Disco/CPU/RAM/Temperatura:** `psutil` do Windows (dados reais da máquina)
- **Tempo de stream:** lido do backend, não inventado
- **Qualidade do streaming:** exibe o bitrate real do Icecast configurado em `config/settings.json` (ou "Indisponível" se streaming não estiver habilitado)

**Arquivos modificados:** `frontend/src/App.jsx`

---

### 1.2 ControlPanel (Painel de Comandos) Ausente
**Problema:** O componente `ControlPanel` estava importado no `App.jsx` mas **nunca renderizado** na tela. Faltavam botões para:
- Gerar playlist do dia (24h)
- Sincronizar acervo musical
- Ativar Spider (varredura do Drive)

**Correção:** O `ControlPanel` foi reinserido na aba de monitoramento (entre o header e o cockpit), com os três botões de comando conectados a chamadas `fetch()` reais na API do backend.

**Arquivos modificados:** `frontend/src/App.jsx`

---

### 1.3 Listener Ntfy — Comandos Não Reconhecidos Variantes
**Problema:** O listener de comandos remotos (`ntfy_listener_service.py`) usava matching por frase exata e frases frágeis, resultando em:
- Não reconhecer variações ("gerar playlist agora", "spider", "sync boletins", etc.)
- Loop de feedback (o listener reagia às próprias notificações)

**Correção:** Implementado sistema robusto de normalização e matching:
- **Normalização de texto:** lowercase, remoção de acentos, remoção de pontuação, colapsagem de espaços
- **Matching tolerante:** substring após normalização + matching por palavras-chave (≥2 de 3 palavras)
- **Sinônimos expandidos:** spider, varrer drive, sync acervo, boletins, checar health, relatório, etc.
- **Anti-loop reforçado:** padrões que identificam mensagens do sistema são filtrados antes do processamento
- **Resposta de erro clara:** quando comando não é reconhecido, retorna ajuda em vez de silenciar

**Arquivos modificados:** `services/ntfy_listener_service.py`

---

### 1.4 Hardcoded Fictício no Backend
**Problema:** `routers/engine.py` contém "Configuração fictícia de streaming" hardcoded (ex.: número fixo de ouvintes, URL fictícia). `scripts/streaming_stats.py` retornava `0` quando streaming não estava habilitado (ambíguo — poderia ser "zero ouvintes" ou "não disponível").

**Correção:**
- `streaming_stats.py`: agora retorna `-1` quando streaming não está habilitado (semântica clara de "não disponível" vs "zero ouvintes")
- `engine.py`: removeda configuração fictícia; `StreamingStats` agora carrega de `config/settings.json`
- Valores reais de `psutil` substituíram placeholders

**Arquivos modificados:** `scripts/streaming_stats.py`, `routers/engine.py`

---

### 1.5 Endpoint de Hardware Real Ausente
**Problema:** O frontend pedia dados de hardware, mas o backend não servia informações reais de uptime, disco, temperatura, etc.

**Correção:** Adicionado `GET /api/status/hardware/realtime` em `routers/status.py` que retorna:
- `uptime_human` / `uptime_seconds`: tempo de atividade do servidor Windows
- `disk`: informações de todos os discos montados (total, usado, livre, %)
- `cpu_temp_celsius`: temperatura do CPU (via psutil)
- `cpu_count` / `cpu_freq`: quantidade e velocidade dos núcleos
- `ram_total_gb` / `ram_available_gb`: memória total e disponível
- `ip_addresses`: todos os IPs de rede ativos
- `ups`: dados de bateria (ou `{charge: -1, voltage: '—', minutes: '—'}` se não disponível)

**Arquivos modificados:** `routers/status.py`

---

### 1.6 Frontend Não Conectado a Dados Reais
**Problema:** O `WebSocketContext.jsx` tinha duplicação de funções de fetch (declaradas duas vezes no mesmo escopo) e não puxava dados de hardware do OS.

**Correção:**
- Removida duplicação de `fetchPlayer`, `fetchHealth`, `fetchQueue` (eram declaradas duas vezes)
- Adicionada `fetchHardware` que consulta `/api/status/hardware/realtime` a cada 5s
- `systemHealth` agora reflete dados reais do servidor

**Arquivos modificados:** `frontend/src/context/WebSocketContext.jsx`

---

### 1.7 Bug Import no `core/monitor.py`
**Problema:** `Optional` não importado (`from typing import Optional` faltava), causando `NameError` no load.

**Correção:** Adicionado `from typing import Optional` ao `core/monitor.py`.

**Arquivo modificado:** `core/monitor.py`

---

## 2. Frontend Rebuild

O frontend foi rebuildado com `npm run build` após todas as alterações nos fontes `.jsx`. O output em `frontend/dist/` agora contém o código compilado com todas as melhorias.

```
dist/index.html                   0.46 kB │ gzip:  0.30 kB
dist/assets/index-nU1RAc6g.css   22.86 kB │ gzip:  5.65 kB
dist/assets/index-DwZsO7RJ.js   279.92 kB │ gzip: 81.06 kB
```

---

## 3. Dependências Instaladas

Foram instaladas as seguintes dependências no venv do Hermes para permitir a execução completa do sistema:

- `pywinauto` — automação de GUI do Windows (ZaraRadio/BUTT)
- `pycaw` — controle de áudio do Windows (PCM)
- `google-genai` — SDK do Google GenAI (substituiu `ollama` que estava faltando)
- `yt-dlp` — downloader de mídia
- `sounddevice`, `soundfile` — áudio em tempo real
- `mutagen` — metadados de áudio
- `numpy`, `librosa` — processamento de áudio
- `psutil`, `requests`, `fastapi`, `uvicorn`, `sqlalchemy`, `apscheduler`, `python-dotenv`, `defusedxml`

---

## 4. Status de Execução

O programa foi lançado e está rodando com sucesso:
- **PID:** processo em background ativo
- **GuardianWorker:** ciclos a cada 2s (monitoramento contínuo)
- **ApiWorker:** ciclos a cada 30s (API health check, score=10, sem violations)
- **API:** escutando na porta 8001
- **Dashboard:** aberto no navegador (http://127.0.0.1:8001)
- **Alertas do Guardian:** detecta silêncio (ex.: "Silêncio detectado por 41s"), verifica processos ativos (ZaraRadio running, BUTT running)

---

## 5. Arquivos Modificados (Resumo)

| Arquivo | Tipo de Mudança |
|---|---|
| `core/monitor.py` | Correção de import (`from typing import Optional`) |
| `frontend/src/App.jsx` | ControlPanel restaurado, MOCKUP 2 com dados reais |
| `frontend/src/context/WebSocketContext.jsx` | Fetch de hardware real, remoção de duplicação de funções |
| `routers/engine.py` | Removido hardcode fictício de streaming |
| `routers/status.py` | Adicionado `GET /hardware/realtime` com dados reais do OS |
| `scripts/streaming_stats.py` | Dados reais (sem hardcode fictício), `-1` quando indisponível |
| `services/ntfy_listener_service.py` | Normalização de texto, matching tolerante, anti-loop reforçado |
| `PLANO_MELHORIAS_RADIO_MANAGER_AGENT.md` | Atualizado com status real das melhorias |
| `frontend/dist/` | Rebuildado com todas as atualizações |