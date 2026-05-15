# 📥 Sistema de Downloads - Guia de Refatoração

## 🎯 O que foi refatorado?

O sistema de downloads teve uma refatoração completa focada em **confiabilidade e manutenibilidade**.

### Principais problemas corrigidos:

1. **Duplicação de código** ❌ → ✅ Centralizado em `YoutubeDLManager`
2. **Error handling silencioso** (`except: pass`) ❌ → ✅ Logging estruturado
3. **Sem retry** ❌ → ✅ 3 tentativas automáticas
4. **Sem timeout** ❌ → ✅ 300s configurável
5. **Progresso instável** ❌ → ✅ UUID v4 confiável

---

## 📁 Arquivos Modificados

### Novos
- **`services/youtube_dl_manager.py`** - Gerenciador centralizado de yt-dlp

### Modificados
- **`services/downloader_service.py`** - Usa YoutubeDLManager, melhor logging
- **`workers/downloader_worker.py`** - Tratamento de erro robusto
- **`routers/downloader.py`** - Logging estruturado

### Teste
- **`test_downloader_refactor.py`** - Script para validar refatoração

---

## 🚀 Executar Testes

```bash
cd c:\Users\STREAMING\.gemini\antigravity\scratch\radio_manager_agent
python test_downloader_refactor.py
```

**Resultado esperado:**
```
✓ Imports: OK
✓ YoutubeDLManager: OK
✓ DownloaderService: OK
✓ DownloaderWorker: OK

Resultado: 4/4 testes passaram
```

---

## 💡 Exemplos de Uso

### Antes (Duplicação)
```python
# Em downloader_service.py - linha 72
ydl_opts = {
    'format': 'bestaudio/best',
    'ffmpeg_location': ...,
    # ... muitas linhas ...
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(query, download=False)

# Em downloader_service.py - linha 113 (DUPLICADO!)
ydl_opts['outtmpl'] = ...
with yt_dlp.YoutubeDL(ydl_opts) as ydl_real:
    ydl_real.download([query])
```

### Depois (Centralizado)
```python
from services.youtube_dl_manager import YoutubeDLManager

manager = YoutubeDLManager()

# Reutiliza opcões
info = manager.extract_info(query, progress_hook=my_hook)
result = manager.download(query, output_path, progress_hook=my_hook)
```

---

## 🔄 Fluxo de Download com Retry

```
Usuario solicita download
        ↓
DownloaderWorker.run_cycle()
        ↓
YoutubeDLManager.download() [Tentativa 1]
    ↓ (erro)
YoutubeDLManager.download() [Tentativa 2]
    ↓ (erro)
YoutubeDLManager.download() [Tentativa 3]
    ↓
✅ Sucesso ou ❌ Falha (log detalhado)
```

---

## 📊 Logging Estruturado

### Exemplo de Sucesso
```
[OmniCore.DownloaderWorker] Iniciando ciclo proativo de aquisição.
[OmniCore.DownloaderWorker] 3 sugestões selecionadas para download automático.
[OmniCore.DownloaderService] Iniciando download: Artista - Música (ID: a1b2c3d4-...)
[OmniCore.DownloaderService] Concluído: Artista - Música -> D:\RADIO\...mp3
[OmniCore.DownloaderWorker] Música catalogada: ARTISTA - Música
```

### Exemplo de Falha com Retry
```
[OmniCore.YoutubeDLManager] Tentativa 1/3 para 'Bad Query'
[OmniCore.YoutubeDLManager] Retry 1/3 após erro: Download error: Video not found
[OmniCore.YoutubeDLManager] Tentativa 2/3 para 'Bad Query'
[OmniCore.YoutubeDLManager] Retry 2/3 após erro: Video not found
[OmniCore.YoutubeDLManager] Tentativa 3/3 para 'Bad Query'
[OmniCore.YoutubeDLManager] Download falhou após 3 tentativas: Video not found
[OmniCore.DownloaderWorker] Download falhou: Bad Query - Video not found
```

---

## ⚙️ Configuração

### Alterar Timeout
```python
from services.downloader_service import DownloaderService

service = DownloaderService()
# Mudar timeout do manager para 600 segundos
service.ydl_manager.timeout_seconds = 600
```

### Alterar Tentativas
```python
from services.youtube_dl_manager import YoutubeDLManager

manager = YoutubeDLManager(max_retries=5)  # Padrão é 3
```

### Alterar Cleanup Delay
```python
service._schedule_cleanup(task_id, delay=120)  # 2 minutos ao invés de 60s
```

---

## 🧪 Como o UUID Melhora o Rastreamento

### Antes (Instável)
```python
task_id = re.sub(r'\W+', '', query)[:20] + "_" + str(os.getpid())
# Resultado: "ArtistaMusicaGreatestHits_1234"
# Problemas:
# - Chaves longas e inconsistentes
# - Colisões se 2 usuarios baixarem mesma música
# - Baseado em PID, não em execução real
```

### Depois (Confiável)
```python
task_id = str(uuid4())
# Resultado: "550e8400-e29b-41d4-a716-446655440000"
# Benefícios:
# - Único globalmente (UUID v4)
# - Comprimento fixo (36 caracteres)
# - Sem risco de colisão
# - Rastreável em logs
```

---

## 🐛 Debugging

### Ver Progresso Ativo
```python
from services.downloader_service import downloader_instance

print(downloader_instance.active_progress)
# {
#     "550e8400-e29b-41d4-a716-446655440000": {
#         "query": "Artista - Música",
#         "percentage": 45.5,
#         "status": "downloading",
#         "speed": "2.5MB/s",
#         "eta": "00:45"
#     }
# }
```

### Habilitar Debug Logging
```python
import logging

logging.getLogger("OmniCore.YoutubeDLManager").setLevel(logging.DEBUG)
logging.getLogger("OmniCore.DownloaderService").setLevel(logging.DEBUG)
```

---

## ✅ Checklist de Validação

- [x] Sintaxe Python válida
- [x] Imports funcionando
- [x] Sem duplicação de ydl_opts
- [x] Error handling sem `except: pass`
- [x] UUID para progresso
- [x] Retry automático (3 tentativas)
- [x] Timeout configurável (300s)
- [x] Logging estruturado com contexto
- [x] Backward compatible (mesma API pública)

---

## 📚 Próximos Passos (Futuro)

1. **Tests unitários** - Mock de yt-dlp para testes rápidos
2. **Async support** - Converter para `async def`
3. **Config via Pydantic** - Centralizar todas as configurações
4. **Métricas** - Exportar sucesso/falha/timeout para observabilidade

---

## 📞 Suporte

Dúvidas ou problemas? Verifique os logs estruturados com prefixo `[OmniCore.Downloader*]`.
