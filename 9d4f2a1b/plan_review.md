# Plan Review: Implement Core ContinuousOrchestrator with APScheduler - Implementation Plan

**Status**: ✅ APPROVED
**Reviewed**: 2026-05-06

## 1. Structural Integrity
- [x] **Atomic Phases**: As fases são lógicas e seguem uma ordem segura de dependência (Estado -> Lógica -> Migração).
- [x] **Worktree Safe**: O plano foca apenas nos arquivos necessários e não depende de estados não commitados de outros tickets.

*Architect Comments*: A separação do estado compartilhado (`CURRENT_MOOD`) em `core/state.py` é uma decisão arquitetural correta para evitar o acoplamento circular que identificamos na pesquisa.

## 2. Specificity & Clarity
- [x] **File-Level Detail**: Os arquivos `core/state.py`, `main.py` e `worker_manager.py` são explicitamente citados.
- [x] **No "Magic"**: O mapeamento `DEFAULT_SCHEDULES` define claramente quais workers serão agendados e com quais intervalos.

*Architect Comments*: O plano é específico o suficiente para ser executado sem ambiguidades.

## 3. Verification & Safety
- [x] **Automated Tests**: O plano prevê a verificação via script de inspeção do scheduler (`scheduler.get_jobs()`).
- [x] **Manual Steps**: Passos de verificação no sistema completo estão presentes.
- [x] **Rollback/Safety**: O uso de `BackgroundScheduler` permite que o sistema continue servindo a API e a UI mesmo se as tarefas de fundo falharem.

*Architect Comments*: Recomendo criar um pequeno script de teste em `tests/test_orchestrator.py` durante a Fase 2 para garantir que o scheduler não apenas tenha os jobs, mas que eles disparem corretamente.

## 4. Architectural Risks
- **Risco de Import Circular**: Identificado e mitigado ao mover o estado para `core/state.py`.
- **Risco de Race Condition**: O APScheduler lida bem com isso, mas o plano menciona o uso de try/except para evitar que falhas individuais derrubem o loop principal.

## 5. Recommendations
- Certifique-se de que o `stop_orchestrator()` seja chamado no encerramento tanto do FastAPI quanto do ícone de bandeja para evitar processos órfãos.
- Adicione um log claro quando o orquestrador iniciar para facilitar o debug remoto.
