---
id: 7b8c9d0e
title: "Dependency Update and Advanced Audio Analysis"
status: Done
priority: High
order: 20
created: 2026-05-06
updated: 2026-05-06
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
---

# Description

## Problem to solve
Current audio analysis is limited to basic energy. The system needs more "musical intelligence" (BPM, Valence, Danceability) to improve transitions and selection.

## Solution
Install advanced audio libraries and modify `CuradoriaWorker` to calculate complex metrics using `librosa`. Update the database schema to store these new fields.

## Implementation Details
- Update `requirements.txt` with `pywinauto`, `pycaw`, `librosa`, `soundfile`.
- Modify `workers/curadoria_worker.py` to use `librosa`.
- Update `core/models.py` with `bpm`, `valence`, `danceability`.
- Implement DB migration.
- Add Reward: +5 for precise analysis.
