# Plan Review: Implement Worker Status and Control API Endpoints

**Status**: ✅ APPROVED
**Reviewed**: 2026-05-06

## 1. Structural Integrity
- [x] **Atomic Phases**: Changes are logically split between router creation and registration.
- [x] **Worktree Safe**: No external dependencies or messy state required.

*Architect Comments*: The phasing is clean. Creating the file before registering it in `main.py` prevents broken imports during implementation.

## 2. Specificity & Clarity
- [x] **File-Level Detail**: Targets `routers/workers.py` and `main.py` specifically.
- [x] **No "Magic"**: Implementation steps for endpoints are clear.

*Architect Comments*: The plan correctly identifies the need to use `worker_manager_instance` and the `health()`/`run_cycle()` methods.

## 3. Verification & Safety
- [x] **Automated Tests**: Mentions unit testing the router logic.
- [x] **Manual Steps**: Reproducible steps using `curl` or browser against Swagger UI.
- [x] **Rollback/Safety**: No destructive database changes.

*Architect Comments*: Verification steps cover both discovery (Swagger) and functional validation (Status and Run).

## 4. Architectural Risks
- **Blocking Calls**: `run_cycle` in `WorkerManager` is synchronous. If a worker takes too long, it could hang the FastAPI thread. However, this project seems to accept this pattern for now (as seen in `bulletins/sync`). 
- **Validation**: Ensure `POST /api/workers/{name}/run` returns a proper 404 if the worker is not found in the registry.

## 5. Recommendations
- When implementing `POST /api/workers/{name}/run`, explicitly handle the "Worker not found" case to return a 404 status code instead of a generic 500.
- Consider adding a `tags=["Workers"]` to the `APIRouter` for better Swagger documentation.

This plan is solid. Proceed to implementation.
