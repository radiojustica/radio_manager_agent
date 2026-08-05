# 🎙️ OMNI CORE V2 - GUIA DE OPERAÇÃO

## ✓ STATUS DO SISTEMA: OPERACIONAL

Data: 04 de Agosto de 2026  
Versão: 2.1.0  
Ambiente: Windows (Python 3.11 em produção / 3.14 no venv do Hermes)

---

## 🚀 COMO INICIAR O SISTEMA

### Opção 1: INICIALIZAÇÃO NORMAL (Recomendada)
```powershell
cd "c:\Users\STREAMING\.gemini\antigravity\scratch
adio_manager_agent"
python main.py
```
**O que acontece:**
- ✓ Carrega todos os workers
- ✓ Inicia API em http://localhost:8001
- ✓ Abre interface Tkinter (oculta) + ícone na bandeja
- ✓ Conecta ao vMix (172.16.217.226:8088)
- ✓ Inicia scheduler de tarefas (APScheduler)

### Opção 2: MODO HEADLESS (Apenas API)
```powershell
python main.py --headless
```
Ideal para manter a API/dashboard no ar sem interface gráfica.

### Opção 3: LAUNCHER Windows
```powershell
START_OMNI.bat
```

---

## 🔒 SEGURANÇA ACÚSTICA (NÃO NEGOCIÁVEL)
1. **ZaraRadio nunca altera o dispositivo de áudio.**
2. **O sistema NUNCA modifica volume automaticamente.** `scripts/audio_manager.py` é estritamente somente-leitura; `core/monitor.py` não chama `SetMasterVolume`.
3. **Volume só por comando manual:** envie `volume NN%` (ex.: `volume 80`) pelo ntfy para ajustar a placa `INTERNO (2- USB Audio CODEC)`. Nunca é automático.

---

## 🕷️ SPIDER (Boletins / Jornais)
O `SpiderWorker` varre o Google Drive (caminho real em `config/settings.json` → `grade.pasta_drive_*`) e abastece:
- `D:\SERVIDOR\BOLETINS\{SEGUNDA..SEXTA}` (boletins diários)
- `D:\SERVIDOR\PROGRAMAS\JORNAL\JORNAL_NJUD.mp3` (jornal mais recente)
- `D:\SERVIDOR\PROGRAMAS\PROGRAMA_40\GIRONASCOMARCAS\GIRO_ATUAL.mp3`
- `D:\SERVIDOR\PROGRAMAS\PROGRAMA_40\LEVEMENTE\LEVEMENTE_ATUAL.mp3`
Disparo: botão "ATIVAR SPIDER" no dashboard ou comando ntfy `spider` / `varrer drive`.

---

## 🔧 COMPONENTES VERIFICADOS

| Componente | Status | Porta | Observações |
|-----------|--------|-------|------------|
| API (FastAPI/Uvicorn) | ✓ OK | 8001 | Respondendo normalmente |
| Database (SQLite) | ✓ OK | - | core/radio_omni.db |
| Guardian Service | ✓ OK | - | Monitorando sistema |
| Workers (autônomos) | ✓ OK | - | Registrados no worker_manager |
| APScheduler | ✓ OK | - | Scheduler ativo |
| vMix Integration | ✓ OK | 8088 | Conectado (172.16.217.226) |
| Frontend | ✓ OK | - | Build em frontend/dist |
| Tray (pystray) | ✓ OK | - | Ícone na bandeja |

---

## 📊 CONFIGURAÇÃO DO SISTEMA

**Arquivo Principal:** [config/settings.json](config/settings.json)

### Paths Configurados (exemplo real):
```json
{
  "grade": {
    "pasta_musicas": "D:\\RADIO\\MUSICAS",
    "pasta_programacao": "D:\\RADIO\\PROGRAMACAO",
    "pasta_vinhetas": "D:\\RADIO\\VINHETAS",
    "pasta_spots": "D:\\RADIO\\SPOTS",
    "pasta_boletins_raiz": "D:\\SERVIDOR\\BOLETINS",
    "pasta_drive_boletins": "D:\\SERVIDOR\\DRIVE\\RADIO TJRN CONTEÚDO\\00_PRODUCAO_2026\\01_BOLETINS_DIARIOS",
    "pasta_drive_njud": "D:\\SERVIDOR\\DRIVE\\RADIO TJRN CONTEÚDO\\00_PRODUCAO_2026\\02_JORNAIS_NJUD"
  }
}
```

---

## 📝 LOGS E DIAGNÓSTICO

### Arquivos de Log:
```
D:\RADIO\LOG ZARARADIO\omni_core.log       (Log principal)
logs/omni_system.log                       (Local em projeto)
logs/radio_agent_*.log                     (Histórico de execuções)
D:\RADIO\logs\engine_history.json          (Histórico de artistas/músicas — anti-repetição)
```

### Verificar Status:
```powershell
# Ver log em tempo real
Get-Content "D:\RADIO\LOG ZARARADIO\omni_core.log" -Tail 50 -Wait

# Ou via API
curl http://localhost:8001/api/status/player/now
curl http://localhost:8001/api/engine/stats
```

---

## 🔗 ACESSO À INTERFACE WEB

```
Dashboard: http://localhost:8001
WebSocket: ws://localhost:8001/ws/status
API Docs: http://localhost:8001/docs
```

---

## 🛠️ TROUBLESHOOTING

### Problema: API não inicia
```powershell
netstat -ano | findstr :8001
python main.py 2>&1 | Out-String
```

### Problema: vMix não conecta
```powershell
Test-NetConnection 172.16.217.226 -Port 8088
```

### Problema: Spider não puxa boletins
Verificar se `config/settings.json` tem `grade.pasta_drive_boletins` apontando para o servidor real (`D:\SERVIDOR\DRIVE\...`). O caminho antigo `H:\Meu Drive\...` não existe.

### Problema: mesmo artista se repete na grade
Verificar `D:\RADIO\logs\engine_history.json` (janela de 30 artistas). O `clean_artist_name` extrai o artista do padrão `ARTISTA - TÍTULO`. Se o metadado estiver vazio, o nome do arquivo deve seguir esse padrão.

---

## 📦 DEPENDÊNCIAS PRINCIPAIS

```
requests, psutil, pycaw, pywin32, comtypes, mutagen,
pytest, fastapi, uvicorn, sqlalchemy, apscheduler,
Pillow, pystray, librosa, soundfile
```

---

## ✅ CHECKLIST DE OPERAÇÃO

- [ ] Sistema iniciado sem erros
- [ ] API respondendo em http://localhost:8001
- [ ] Guardian Service monitorando
- [ ] Workers registrados e ativos
- [ ] vMix conectado
- [ ] Diretórios D:\RADIO\* e D:\SERVIDOR\* existem e são acessíveis
- [ ] Logs sendo gerados
- [ ] Dashboard web acessível
- [ ] WebSocket conectado para live updates
- [ ] Spider consegue puxar boletins (testar "ATIVAR SPIDER")

---

## 📞 SUPORTE

1. Verificar logs em `D:\RADIO\LOG ZARARADIO\`
2. Consultar [docs/AUDIT_DOCUMENTATION.md](docs/AUDIT_DOCUMENTATION.md)
3. Consultar [docs/regras_programacao.md](docs/regras_programacao.md)

---

**Omni Core V2 - Sistema de Automação de Rádio**  
Versão: 2.1.0 | Data: 2026-08-04 | Status: ✓ OPERACIONAL

