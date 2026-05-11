---
id: 2d4e5f6a
title: "Architectural Refactoring and Worker Integration"
status: Done
priority: High
order: 10
created: 2026-05-06
updated: 2026-05-07
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
---

# Description

## Problem to solve
`main.py` is a monolith handling UI, API, and orchestration logic. This makes the system fragile and hard to maintain.

## Solution
Deconstruct `main.py` into specialized modules (`core/system.py`, `api/manager.py`, `gui/`) and integrate all background logic into the `WorkerManager`. Implement `ButtWorker` for automated streaming management.

## Implementation Details
- Move system initialization to `core/system.py`.
- Move API lifecycle to `api/manager.py`.
- Move UI logic to `gui/console.py` and `gui/tray.py`.
- Create `workers/butt_worker.py` (inheriting `WorkerBase`).
- Integrate `ButtWorker` into `WorkerManager` scheduler.
- Configure intervals in `settings.json`.

## Implementation Summary
- `main.py` now delegates system startup, API lifecycle, and UI control to modular packages.
- `core/system.py` handles admin elevation and single-instance mutex.
- `api/manager.py` handles FastAPI startup, health wait, and dashboard launch.
- `gui/console.py` and `gui/tray.py` encapsulate local UI and tray interactions.
- `WorkerManager` now registers `ButtWorker` and schedules it dynamically from config.
