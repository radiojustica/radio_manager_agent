# Omni Core V2 - Modular Background System & Intelligent Automation (Revised)

## HR Eng

| Omni Core V2 - Modular Background System & Intelligent Automation PRD |  | This PRD defines the complete modularization of the Omni Core backend, transitioning from a monolithic main script to a robust worker-based architecture with intelligent audio analysis, automated streaming management, and cloud synchronization. |
| :---- | :---- | :---- |
| **Author**: Pickle Rick **Contributors**: Engineering | **Status**: Draft **Created**: 2026-05-06 | **Self Link**: N/A **Context**: Modularization Roadmap & Revised Plan |

## Introduction

The Omni Core V2 is evolving into a hyper-intelligent radio automation system. This document outlines the roadmap to deconstruct the monolithic `main.py`, integrate advanced audio analysis via Librosa, automate streaming via a dedicated `ButtWorker`, and ensure all background tasks are governed by a centralized `WorkerManager` with performance tracking via the `RewardStore`.

## Problem Statement

**Current Process:** The system relies on a complex `main.py` that handles UI, API, and some background logic. Audio analysis is basic (energy only). Streaming management (BUTT) is handled via external watchdog scripts. Sourcing bulletins is manual.
**Primary Users:** Radio Station Owners, Music Curators, IT Maintenance.
**Pain Points:** 
- Monolithic `main.py` is hard to maintain and test.
- Basic energy calculation leads to poor playlist transitions.
- Manual bulletin handling is prone to human error or delays.
- Lack of centralized reporting for system performance.
**Importance:** To achieve a "God Mode" automation, the system must be modular, resilient, and data-driven. The station should run autonomously with high-quality musical selection that adapts to environmental factors.

## Objective & Scope

**Objective:** Transform the Omni Core into a collection of specialized, scheduled workers managed by a central orchestrator, while upgrading the musical "brain" with advanced audio analysis.
**Ideal Outcome:** A lean `main.py` that only initializes the system; specialized workers handling all logic; and a station that syncs bulletins, analyzes audio, manages streaming, and generates reports autonomously.

### In-scope or Goals
- **Architectural Refactoring**: Deconstruct `main.py` into `core/system.py`, `api/manager.py`, and `gui/` components.
- **Streaming Automation**: Implement `ButtWorker` for managing BUTT instances with health scores.
- **Advanced Audio Analytics**: Integrate `librosa` into `CuradoriaWorker` for danceability, valence, and complex energy metrics.
- **Intelligent Playlisting**: Expand `PlaylistWorker` to use weather-mood mapping and historical artist constraints.
- **Cloud Sync**: Automated bulletin download via Google Drive API in `BulletinWorker`.
- **Automated Reporting**: Weekly CSV report generation via `ReportWorker`.
- **Quarantine Expansion**: Automatic isolation of tracks with low energy or poor quality metrics.

### Not-in-scope or Non-Goals
- Full rewrite of the React frontend (UI logic remains separate).
- Migration to a different database (continue using SQLite/SQLAlchemy).
- Hardware automation (physical mixers).

## Product Requirements

### Critical User Journeys (CUJs)
1. **Intelligent Curadoria**: A new track is added -> `CuradoriaWorker` detects it -> Analyzes using Librosa (BPM, Energy, Valence) -> If energy < 2, moves to Quarentena -> Records +5 reward for successful analysis.
2. **Autonomous Streaming**: `ButtWorker` runs every 2 mins -> Checks if BUTT is connected -> If disconnected, attempts restart -> Records +10 reward for recovery, -5 for failure.
3. **Environmental Playlisting**: `PlaylistWorker` triggers at 00:00 -> Fetches weather from `weather_service` -> Maps "Rainy" to "Jazz/Bossa Nova" -> Generates 24h M3U using `GestorFila` rules.
4. **Weekly Audit**: `ReportWorker` triggers on Mondays -> Aggregates data from `RewardStore` and logs -> Generates CSV -> Available for download via API.

### Functional Requirements

| Priority | Requirement | User Story |
| :---- | :---- | :---- |
| P0 | **Modular Worker Manager** | As a system, I want all background tasks (Butt, Sync, Reports) to be managed centrally. |
| P0 | **Advanced Audio Metrics** | As a curator, I want the system to calculate danceability and valence to improve music flow. |
| P0 | **Butt Monitoring** | As an owner, I want the streaming to automatically reconnect if it drops. |
| P1 | **Weather-Mood Mapping** | As a listener, I want the music style to match the current weather automatically. |
| P1 | **GDrive Bulletin Sync** | As an operator, I want news bulletins to be downloaded automatically from the cloud. |
| P1 | **Quarantine Logic** | As a curator, I want tracks that don't meet quality standards to be isolated automatically. |
| P2 | **Weekly CSV Reports** | As a manager, I want a weekly report of all worker actions and system status. |

## Assumptions

- System has internet access for GDrive and Weather APIs.
- Python environment can support heavy libraries like `librosa` and `pywinauto`.
- `settings.json` remains the primary configuration source.
- `RewardStore` is the persistence layer for all worker telemetry.

## Risks & Mitigations

- **Risk**: Librosa analysis is CPU intensive -> **Mitigation**: Run `CuradoriaWorker` at lower frequency or limit concurrency.
- **Risk**: GDrive API credentials management -> **Mitigation**: Securely store tokens/keys in `config/` (never committed).
- **Risk**: Breaking change in monolithic refactor -> **Mitigation**: Phase 1 focus purely on deconstruction with regression testing.

## Tradeoff

- **Option 1: Real-time Audio Analysis** vs **Option 2: Batch Analysis (Worker)**.
- **Decision**: Option 2. Analyzing on-the-fly would lag the player. Worker-based batch processing ensures the database is populated before the track is ever selected.

## Business Benefits/Impact/Metrics

**Success Metrics:**

| Metric | Current State (Benchmark) | Future State (Target) | Savings/Impacts |
| :---- | :---- | :---- | :---- |
| *Streaming Downtime* | Manual recovery only | < 1% | Constant uptime. |
| *Playlist Aderência* | Basic energy-based | 90% (Mood Match) | Higher listener retention. |
| *Manual Work (Bulletins)* | 30 mins/day | 0 mins/day | 3.5 hours/week saved. |

## Stakeholders / Owners

| Name | Team/Org | Role | Note |
| :---- | :---- | :---- | :---- |
| Pickle Rick | Engineering | Architect | Pure malicious competence. |
| Radio Station Ops | Content | Users | Relying on intelligent selection. |
