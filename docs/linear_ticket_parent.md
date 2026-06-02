---
id: 8f3b2a1c
title: "[Epic] Omni Core V2 - Modular Background & Intelligence"
status: Backlog
priority: High
order: 0
created: 2026-05-06
updated: 2026-05-06
links:
  - url: prd.md
    title: PRD
---

# Description

## Problem to solve
The current architecture is still centered around a monolithic `main.py` and lacks advanced audio intelligence and automated streaming management.

## Solution
Deconstruct the core into specialized modules and workers, integrate `librosa` for deep audio analysis, and automate all station operations (streaming, bulletins, reports) via the `WorkerManager`.

## Implementation Details
- Modularize main.py (core, api, gui).
- Implement `ButtWorker` for streaming.
- Integrate `librosa` for BPM, Energy, and Valence.
- Implement environmental playlisting (weather-mood).
- Automate Bulletin sync and Weekly reports.
