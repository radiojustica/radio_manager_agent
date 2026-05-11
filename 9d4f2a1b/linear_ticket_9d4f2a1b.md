---
id: 9d4f2a1b
title: "Implement Core ContinuousOrchestrator with APScheduler"
status: Done
priority: High
order: 10
created: 2026-05-06
updated: 2026-05-06
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
  - url: plan_20260506.md
    title: Implementation Plan
  - url: research_20260506.md
    title: Research Document
  - url: plan_review.md
    title: Plan Review
---

# Description

## Problem to solve
Workers exist but there is no centralized mechanism to schedule their execution cycles automatically.

## Solution
Integrate `APScheduler` (BackgroundScheduler) into `WorkerManager` or create a wrapper class `ContinuousOrchestrator`. Define a method to start the scheduler and register worker jobs based on a default interval.

## Implementation Details
- Inject `APScheduler` into `WorkerManager`.
- Add `start_orchestrator()` method.
- Ensure only one scheduler runs.
- Map workers to their default intervals (e.g., Weather: 30m, Sync: 1h, Playlist: Daily at 00:00).
- Integrate with `main.py` startup.
