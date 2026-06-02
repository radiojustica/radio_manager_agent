# BLUEPRINT: Omni Core V2 - Radio Station Intelligence

## 1. Visão Geral
O **Omni Core V2** é um sistema unificado de gestão e automação para estações de rádio, integrando o motor de playlisting inteligente, monitoramento de processos críticos (ZaraRadio, BUTT) e um Dashboard Web de alta performance para controle remoto e telemetria.

---

## 2. Arquitetura Técnica
- **Backend**: Python (FastAPI) servindo como Hub Central e API.
- **Frontend**: React.js (Vite) para a interface de monitoramento e curadoria.
- **Banco de Dados**: SQLite (SQLAlchemy) gerenciando ~8000 faixas com metadados de energia e gênero.
- **Automação**: APScheduler para jobs cronometrados (Geração às 00:00).
- **Interface Desktop**: Tkinter integrado para controle local e ícone de bandeja (System Tray).
- **Sistema de Workers**: Framework orquestrado com `WorkerManager`, herança de `WorkerBase` e tracking de performance via `RewardStore` (scores baseados em sucesso/falha).
- **Resiliência**: Watchdog dedicado (`omni_watchdog.py`) para garantir 99.9% de uptime do serviço.

---

## 3. Implementações Executadas (Status: ✅ Concluído)
- [x] **Motor de Playlist**: Geração automática de blocos de 24h as 00:00 com regras de clima (Mood) e gêneros.
- [x] **Guardian Service**: Monitoramento ativo de travamentos no ZaraRadio e queda de conexão nos encoders BUTT.
- [x] **Dashboard Telemetry**: 
    - Painel responsivo e modo tela cheia para monitoramento de estúdio.
    - Exibição de estatísticas do acervo (Top gêneros, total de faixas).
    - Status de energia acústica em tempo real (via Librosa/SQL).
- [x] **System Tray Controller**: Atalhos rápidos para geração manual, sincronia e recarregamento de configs.
- [x] **Logging Centralizado**: Redirecionamento de logs críticos para `D:\RADIO\LOG ZARARADIO`.
- [x] **Controle de Janela**: Botão no dashboard para restaurar a interface do backend remotamente.
- [x] **Sistema de Workers**: Framework com recompensas (scores) para otimização de performance.

---

## 4. Implementações Concluídas (Status: ✅ OK)
- [x] **Integração vMix**: Gatilho automático de cenas baseado no metadado da música (Abertura/Encerramento).
- [x] **Módulo de Quarentena**: Automação para mover arquivos com erro ou baixa energia para a pasta de quarentena.
- [x] **Relatórios de Execução**: Geração automática de relatórios CSV semanais sobre as músicas mais tocadas.
- [x] **Central de Boletins (GDrive)**: Sincronização inteligente de boletins jornalísticos do Drive para a rede local (D:\SERVIDOR\BOLETINS).
    - [x] Filtro automático de áudios de edição (OFF/GRAVACAO).
    - [x] Visor de datas e botão de sync manual no Cockpit.
    - [x] Sincronia automática pré-geração de grade 24h.

## 5. Implementações Pendentes (Status: 🕒 Em Fila)
- [ ] **Notificações Push**: WhatsApp (Configurado via Webhook, aguarda endpoint da Evolution/Z-API).

---

## 6. Roadmap V3 - Incorporação de Features Avançadas (Em Andamento)
### Fase 1: Refatoração Arquitetural e Workers (Semanas 1-2)
- [ ] **Modularização**: Quebrar `main.py` em `core/system.py`, `api/manager.py`, `gui/console.py`, `gui/tray.py`.
- [ ] **Integração ButtWorker**: Novo worker para gerenciamento de cluster BUTT com recompensas (+10/-5).
- [ ] **Atualização Dependências**: Adicionar `librosa`, `soundfile`, `pywinauto`, `pycaw`, `comtypes`.
- [ ] **Melhoria Análise Áudio**: Usar Librosa para métricas avançadas (danceability, valence) no CuradoriaWorker.

### Fase 2: Inteligência e Monitoramento (Semanas 3-4)
- [ ] **Motor Playlisting Inteligente**: Integrar clima/horário ao PlaylistWorker com `GestorFila`.
- [ ] **Relatórios CSV Semanais**: Criar ReportWorker com job semanal e scores (+20/-10).
- [ ] **Sincronização Boletins GDrive**: BulletinWorker com filtros automáticos (+15/-5).
- [ ] **Expansão Quarentena**: Critérios avançados no CuradoriaWorker.

### Fase 3: Utilitários e Otimização (Semana 5)
- [ ] **Scripts de Manutenção**: `reset_definitivo_v2.py` adaptado.
- [ ] **Documentação**: Guias em `docs/` e atualização deste blueprint.
- [ ] **Testes e Validação**: Cobertura completa com scores de performance.

**Cronograma Total**: 5 semanas (28-38 horas).
**Sistema de Recompensas**: Aplicado a todos os workers via `RewardStore` para otimização automática baseada em performance.


---

## 6. Guia de Manutenção
- **Logs**: Localizados em `D:\RADIO\LOG ZARARADIO\omni_system.log`.
- **Banco de Dados**: `radio_omni.db` na raiz do projeto.
- **Configurações**: `config/settings.json`.
- **Startup**: O arquivo `main.py` (ou `OmniCoreV2.exe`) deve ser iniciado junto com o Windows, monitorado pelo `omni_watchdog.py`.

---
*Última Atualização: 14 de Abril de 2026*
