---
id: 5e6f7g8h
title: "Weekly CSV Report Generation and Reward Audit"
status: Done
priority: Medium
order: 40
created: 2026-05-06
updated: 2026-05-13
links:
  - url: ../linear_ticket_parent.md
    title: Parent Ticket
---

# Description

## Problem to solve
Station performance (worker success/failures) is stored in `worker_rewards.json` but there is no automated summary or export for management.

## Solution
Implement a `ReportWorker` that generates a CSV summary of all worker activities and rewards every week.

## Implementation Details
- Create `workers/report_worker.py`.
- Implement `weekly_csv_generator.py` logic.
- Add API endpoint for manual report download.
- Add Reward: +20 for report generation.
