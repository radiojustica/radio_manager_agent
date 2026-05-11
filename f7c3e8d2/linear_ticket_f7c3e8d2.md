---
id: f7c3e8d2
title: "Implement Worker Status and Control API Endpoints"
status: Done
priority: High
order: 20
created: 2026-05-06
updated: 2026-05-06
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
  - url: research_20260506.md
    title: Research Document
  - url: research_review.md
    title: Research Review
  - url: plan_20260506.md
    title: Implementation Plan
  - url: plan_review.md
    title: Plan Review
---

# Description

## Problem to solve
The frontend has no way to query the current state, health, or last run time of the modular workers.

## Solution
Add FastAPI routes to expose worker telemetry and provide a "Run Now" trigger.

## Implementation Details
- Create `routers/workers.py` (or update `routers/status.py`).
- Endpoint `GET /api/workers/status`: Returns a list of all registered workers, their health score, and last execution metadata.
- Endpoint `POST /api/workers/{name}/run`: Manually triggers a worker cycle.
- Ensure the API uses the global `worker_manager_instance`.
