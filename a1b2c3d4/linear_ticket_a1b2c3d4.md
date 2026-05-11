---
id: a1b2c3d4
title: "Implement Dynamic Scheduling and Fault Tolerance"
status: Done
priority: Medium
order: 30
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
Worker intervals are currently hardcoded, and a single worker crash might destabilize the cycle.

## Solution
Load worker intervals from `settings.json` and wrap `run_cycle` in a robust try/except block that logs failures to the `RewardStore` without stopping the orchestrator.

## Implementation Details
- Update `config/settings.json` to include a `workers` section with intervals.
- Refactor `WorkerManager.run_cycle` to handle all exceptions.
- Implement automatic reload of schedules if `settings.json` changes (optional/bonus) or at least ensure clean initialization.
- Log "CRITICAL_FAILURE" to `RewardStore` when an unhandled exception occurs in a worker.
