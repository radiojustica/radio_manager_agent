---
id: 3m4n5o6p
title: "Advanced Quarantine and Quality Isolation"
status: Done
priority: Low
order: 60
created: 2026-05-06
updated: 2026-05-13
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
---

# Description

## Problem to solve
Poor quality tracks or tracks with low energy can disrupt the station's vibe and listener experience.

## Solution
Expand the `CuradoriaWorker` with quarantine criteria based on advanced audio metrics (e.g., Energy < 2, high centroid variance).

## Implementation Details
- Update `CuradoriaWorker` logic to include automated quarantine moves.
- Implement API endpoint for manual quarantine review.
- Add Reward: +5 for correct isolation.
