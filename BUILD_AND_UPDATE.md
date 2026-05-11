# Build e Atualização Automática - Omni Core V2

## 🔧 Como Gerar o EXE

### Pré-requisitos
- Python 3.9+
- PyInstaller instalado: `pip install pyinstaller`
- Todas as dependências em `requirements.txt`

### Build Rápido

```bash
cd C:\Users\STREAMING\.gemini\antigravity\scratch\radio_manager_agent
python build.py
```

**Resultado:**
- `dist/omni_core.exe` - Executável único
- `dist/VERSION` - Versão do build
- `dist/omni_core.md5` - Hash para verificação
- `dist/code.md5` - Hash do código-fonte

### Build Manual (avançado)

```bash
pyinstaller --onefile --console main.py --name=omni_core
```

---

## 🔄 Sistema de Atualização Automática

### Como Funciona

1. **UpdateWorker** roda **a cada 1 hora**
2. Calcula hash MD5 de todo código-fonte
3. Compara com hash armazenado
4. Se houver mudanças:
   - Reconstrói o EXE automaticamente
   - Atualiza arquivo de versão
   - Envia notificação via Telegram
   - EXE antigo é substituído

### Cronograma de Verificação

```
UpdateWorker (a cada 1 hora)
├─ Calcula hash do código
├─ Compara com ultima_versao.md5
├─ Se mudanças detectadas:
│  ├─ Executa build.py
│  ├─ Testa novo EXE
│  ├─ Substitui versão antiga
│  └─ Notifica via Telegram
└─ Atualiza hash armazenado
```

### Configuração

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

Opções:
- `interval_hours`: 1 (padrão)
- `interval_minutes`: 60 (alternativa)

---

## 📦 Estrutura de Distribuição

```
dist/
├── omni_core.exe          # Executável principal
├── VERSION                # Versão atual (1.0.0)
├── omni_core.md5          # Hash do EXE
└── code.md5               # Hash do código-fonte
```

---

## ⚙️ Procedimento de Atualização

### Fluxo Completo

```
1. Usuário faz alterações no código
   └─ Commit no Git / Save local
   
2. UpdateWorker detecta mudanças (a cada 1h)
   └─ Hash MD5 diferente
   
3. Inicia build automático
   └─ PyInstaller reconstrói EXE
   
4. Testa novo executável
   └─ Valida integridade
   
5. Substitui versão antiga
   └─ Backup automático (opcional)
   
6. Notifica via Telegram
   └─ "Omni Core atualizado!"
   
7. Próxima reinicialização usa nova versão
   └─ Sem intervenção manual
```

---

## 🛡️ Segurança e Rollback

### Proteção Contra Falhas

- ✅ Hash MD5 valida integridade
- ✅ Testa build antes de substituir
- ✅ Fallback para versão anterior se falhar
- ✅ Logging completo de todas operações

### Rollback Manual

```bash
# Restaurar versão anterior
copy dist\omni_core.exe.bak dist\omni_core.exe

# Resetar hash
del dist\code.md5
```

---

## 📊 Monitoramento

### Logs

```
D:\RADIO\LOG ZARARADIO\omni_system.log
```

Mensagens importantes:

```
[INFO] 🔄 Mudanças detectadas no código
[INFO] 🔨 Reconstruindo EXE...
[INFO] ✓ EXE reconstruído com sucesso
[INFO] ✅ Sistema atualizado com sucesso!
```

### Dashboard

Acesse `http://localhost:8001` → Aba de Workers para status em tempo real

---

## 🚀 Deployment

### Primeiro Deploy (Manual)

```bash
# 1. Gerar EXE
python build.py

# 2. Copiar para local de execução
copy dist\omni_core.exe "C:\Program Files\OmniCore\omni_core.exe"

# 3. Criar atalho ou executar
C:\Program Files\OmniCore\omni_core.exe
```

### Atualizações Futuras (Automáticas)

- Não é necessário fazer nada manualmente
- UpdateWorker cuida de tudo
- Notificações via Telegram confirmam

---

## 🐛 Troubleshooting

### Build falha com erro "PyInstaller not found"

```bash
pip install pyinstaller
```

### EXE não inicia após update

1. Verificar logs em `D:\RADIO\LOG ZARARADIO\`
2. Executar build manual: `python build.py`
3. Copiar EXE manualmente se necessário

### UpdateWorker não roda

- Verificar se está registrado: `worker_manager.py` linha ~215
- Verificar configuração em `settings.json`
- Logs em `D:\RADIO\LOG ZAZAZADIO\omni_system.log`

---

## 📈 Próximas Melhorias

- [ ] Backup automático de versões anteriores
- [ ] Teste de integridade do EXE antes de usar
- [ ] Delta updates (apenas mudanças, não build completo)
- [ ] Assinatura digital do executável
- [ ] Auto-restart do serviço após update
