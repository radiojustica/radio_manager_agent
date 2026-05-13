---
id: 9i0j1k2l
title: "Google Drive Bulletin Synchronization"
status: Done
priority: Medium
order: 50
created: 2026-05-06
updated: 2026-05-06
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
---

# Description

## Problem to solve
News bulletins must be manually downloaded and organized, leading to potential delays in the station's information schedule.

## Solution
Implement a `BulletinWorker` that uses the Google Drive API to fetch the latest bulletins automatically, applying filters for 'OFF' or 'GRAVACAO'.

## Implementation Details
- Create `workers/bulletin_worker.py`.
- Integrate Google Drive API in `bulletin_sync.py`.
- Implement daily sync job before playlist generation.
- Add Reward: +15 for successful sync.
