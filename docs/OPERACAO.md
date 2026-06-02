# 🎙️ OMNI CORE V2 - GUIA DE OPERAÇÃO

## ✓ STATUS DO SISTEMA: OPERACIONAL

Data: 13 de Maio de 2026  
Versão: 2.0.0  
Ambiente: Windows Python 3.14

---

## 📋 RESUMO DAS CORREÇÕES APLICADAS

### ✓ Problema 1: Importação incorreta em api/start_api.py
**Status:** RESOLVIDO

```python
# ❌ ANTES (linha 2):
from main import app

# ✓ DEPOIS:
from api.manager import app
```

**Arquivo corrigido:** [api/start_api.py](api/start_api.py#L2)

---

### ✓ Problema 2: Elevação de admin problemática
**Status:** RESOLVIDO

O sistema foi modificado para permitir execução sem privilégios elevados:

- **Arquivo:** [core/system.py](core/system.py#L30)
- **Mudança:** Função `run_as_admin()` agora retorna `bool` em vez de chamar `sys.exit()`
- **Arquivo:** [core/launcher.py](core/launcher.py#L18)
- **Mudança:** Launcher permite execução mesmo se elevação falhar

---

## 🚀 COMO INICIAR O SISTEMA

### Opção 1: INICIALIZAÇÃO NORMAL (Recomendada)
```powershell
cd "c:\Users\STREAMING\.gemini\antigravity\scratch\radio_manager_agent"
python start.py
```

**O que acontece:**
- ✓ Carrega todos os workers
- ✓ Inicia API em http://localhost:8001
- ✓ Abre interface Tkinter
- ✓ Conecta ao vMix (172.16.217.226:8088)
- ✓ Inicia scheduler de tarefas

---

### Opção 2: TESTE DE DIAGNÓSTICO
```powershell
python test_startup.py
```

**Output esperado:**
```
✓ Imports: OK
✓ API: Iniciada (http://0.0.0.0:8001)
✓ Workers: 10 registrados
✓ Scheduler: APScheduler funcionando
✓ Guardian Service: OK
✓ vMix Integration: Conectado
```

---

### Opção 3: MODO CLÁSSICO (Compatibilidade)
```powershell
python main.py
```

> Nota: Este modo tenta elevar para admin, mas o sistema continua mesmo se falhar.

---

## 🔧 COMPONENTES VERIFICADOS

| Componente | Status | Porta | Observações |
|-----------|--------|-------|------------|
| API (FastAPI/Uvicorn) | ✓ OK | 8001 | Respondendo normalmente |
| Database (SQLite) | ✓ OK | - | core/radio_omni.db |
| Guardian Service | ✓ OK | - | Monitorando sistema |
| Workers (10 total) | ✓ OK | - | Todos registrados |
| APScheduler | ✓ OK | - | Scheduler ativo |
| vMix Integration | ✓ OK | 8088 | Conectado (172.16.217.226) |
| Frontend | ✓ OK | - | Build presente em frontend/dist |
| Tkinter GUI | ⚠️ Requer Admin | - | Para acesso completo |

---

## 📊 CONFIGURAÇÃO DO SISTEMA

**Arquivo Principal:** [config/settings.json](config/settings.json)

### Paths Configurados:
```json
{
  "paths": {
    "programacao": "D:\\RADIO\\PROGRAMACAO",
    "programa_musicas": "D:\\PROGRAMA_MUSICAS"
  },
  "grade": {
    "pasta_musicas": "D:\\RADIO\\MUSICAS",
    "pasta_programacao": "D:\\RADIO\\PROGRAMACAO",
    "pasta_vinhetas": "D:\\RADIO\\VINHETAS",
    "pasta_spots": "D:\\RADIO\\SPOTS",
    "pasta_boletins_raiz": "D:\\SERVIDOR\\BOLETINS"
  }
}
```

### Verificar Conectividade:
1. **ZaraRadio:** Necessário para operação completa
2. **vMix:** Status verificável via HTTP 172.16.217.226:8088
3. **Diretórios D:\RADIO\*:** Devem existir e ser acessíveis

---

## 📝 LOGS E DIAGNÓSTICO

### Arquivos de Log:
```
D:\RADIO\LOG ZARARADIO\omni_core.log       (Log principal)
D:\RADIO\LOG ZARARADIO\test_startup.log    (Teste de inicialização)
logs/omni_system.log                       (Local em projeto)
logs/radio_agent_*.log                     (Histórico de execuções)
```

### Verificar Status:
```powershell
# Ver log em tempo real
Get-Content "D:\RADIO\LOG ZARARADIO\omni_core.log" -Tail 50 -Wait

# Ou via API
curl http://localhost:8001/api/status
```

---

## 🔗 ACESSO À INTERFACE WEB

Quando o sistema estiver rodando:

```
Dashboard: http://localhost:8001
WebSocket: ws://localhost:8001/ws/status
API Docs: http://localhost:8001/docs
```

---

## 🛠️ TROUBLESHOOTING

### Problema: "Não é admin, tentando solicitar elevação..."
**Solução:** Sistema continua normalmente em modo reduzido. Para acesso completo:
1. Abra PowerShell como Administrador
2. Execute: `python start.py`

### Problema: API não inicia
**Verificar:**
```powershell
# Verificar porta 8001
netstat -ano | findstr :8001

# Verificar imports
python test_startup.py

# Ver erro completo
python main.py 2>&1 | Out-String
```

### Problema: vMix não conecta
**Verificar:**
```powershell
# Testar conectividade
Test-NetConnection 172.16.217.226 -Port 8088

# Ver logs
Get-Content logs\engine_history.json
```

---

## 📦 DEPENDÊNCIAS INSTALADAS

```
requests>=2.33.0
pywinauto>=0.6.9
psutil>=7.2.2
pycaw>=20251023
pywin32>=311
comtypes>=1.4.16
mutagen>=1.47.0
pytest>=9.0.3
fastapi>=0.111.0
uvicorn>=0.30.0
sqlalchemy>=2.0.0
apscheduler>=3.10.0
Pillow>=10.3.0
pystray>=0.19.0
librosa>=0.10.1
soundfile>=0.12.1
```

---

## ✅ CHECKLIST DE OPERAÇÃO

- [ ] Sistema iniciado sem erros
- [ ] API respondendo em http://localhost:8001
- [ ] Guardian Service monitorando
- [ ] Workers registrados e ativos
- [ ] vMix conectado
- [ ] Diretórios D:\RADIO\* existem e são acessíveis
- [ ] Logs sendo gerados em D:\RADIO\LOG ZARARADIO\
- [ ] Dashboard web acessível
- [ ] WebSocket conectado para live updates

---

## 📞 SUPORTE

Para problemas ou questões:
1. Verificar logs em `D:\RADIO\LOG ZARARADIO\`
2. Executar `python test_startup.py` para diagnóstico
3. Revisar arquivo `LAUNCHER_README.md`

---

**Omni Core V2 - Sistema de Automação de Rádio**  
Versão: 2.0.0 | Data: 2026-05-13 | Status: ✓ OPERACIONAL
