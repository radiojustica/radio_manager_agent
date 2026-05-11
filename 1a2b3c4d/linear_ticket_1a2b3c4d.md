---
id: 1a2b3c4d
title: "Intelligent Playlisting with Weather-Mood Mapping"
status: Todo
priority: High
order: 30
created: 2026-05-06
updated: 2026-05-06
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
---

# Description

## Problem to solve
Playlists are generated with basic energy rules but don't adapt to the current weather or complex mood transitions.

## Solution
Integrate `GestorFila` rules into `PlaylistWorker` and add weather-based genre mapping. Update `weather_service.py` to support mood-based queries.

## Implementation Details
- Modify `workers/playlist_worker.py` to include mood mapping (Weather -> Gêneros).
- Use `weather_service.py` for real-time climate data.
- Integrate `GestorFila` for anti-repetition and energy curves.
- Add Reward: +10 for high-adherence playlist generation.
