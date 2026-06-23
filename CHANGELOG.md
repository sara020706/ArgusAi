# Changelog

All notable changes to Argus are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [0.1.0] — 2026-06-23

### Added

- **Phase 1: Core scoring engine** — feature extraction, heuristic rules (7 rules, 0–50 pts each), statistical deviation scoring with Welford z-score bands, risk banding (LOW/MEDIUM/HIGH/CRITICAL), and human-readable ASCII explanation renderer. Zero external dependencies.
- **Phase 2: Storage interface** — `ArgusStore` abstract base class, `SQLiteStore` (stdlib `sqlite3`, two-table schema, JSON-serialized fields), `MemoryStore` (dict-backed, for tests). `UserProfile` with Welford's online algorithm for incremental mean/variance updates. `ArgusEngine` for stateful scoring: loads profile → scores → updates baseline → persists.
- **Phase 2: Cold-start handling** — first-ever event for a user is never penalized for novel IP or device; the profile seeds itself from the first event.
- **Phase 3: IsolationForestDetector** — optional scikit-learn anomaly detector, import-guarded so the core package installs without sklearn. Contributes up to 20 additional points. Supports `save()`/`load()` for model persistence.
- **Phase 3: Synthetic dataset generator** — generates realistic normal and anomalous events for five user archetypes (analyst, developer, executive, sysadmin). Used by `ArgusEngine.train()` to bootstrap the ML model.
- **Phase 4: Multi-event correlation engine** — five attack patterns detected over a 24-hour sliding window: `repeated_night_logins`, `escalating_downloads`, `reconnaissance`, `slow_exfiltration`, `account_takeover_indicators`. Bonus points capped so final score never exceeds 100. Never raises — returns `(0.0, [])` on any error.
- **Phase 4: ThreatIntelClient** — AbuseIPDB integration via stdlib `urllib`. Private/RFC1918 IPs never looked up. In-memory cache with configurable TTL. Contributes 0–40 points depending on confidence score. Operates without an API key (returns neutral result).
- **Phase 5: FastAPI REST server** — full OpenAPI docs at `/docs`. Endpoints: `POST /v1/events/score`, `POST /v1/events/batch` (max 100), `GET /v1/alerts`, `GET /v1/alerts/stats`, `GET /v1/users/{id}/profile`, `GET /v1/users/{id}/events`, `GET /v1/users/{id}/risk_summary`, `GET /health`, `GET /metrics`. Optional `X-API-Key` middleware. Exposed as `argus-serve` console script.
- **Phase 6: Streamlit SOC dashboard** — multi-page dark-theme dashboard: Overview (live metrics), Alerts (filterable table), User Profiles (baseline charts), Threat Map. Exposed as `argus-dashboard` console script. `api_client.py` with safe fallbacks for all 9 API calls.
- **Phase 7: AuthCollector** — reads Linux `auth.log`, CSV, and JSON Lines formats. Auto-detects format from first line. Incremental reads via byte-offset `_last_position`.
- **Phase 7: NetworkCollector** — reads NetFlow CSV and simple traffic log formats. Aggregates per-packet events into per-user time-window events. Optional live PyShark capture (guarded import).
- **Phase 7: FileCollector** — reads auditd and CSV file-access logs. Groups file touches into per-user, per-window `Event` objects. Optional live watchdog monitoring (guarded import).
- **Phase 7: Simulation helpers** — `simulate_auth_log()`, `simulate_network_log()`, `simulate_file_log()` write realistic synthetic log files to disk. `run_simulation()` drives an `ArgusEngine` end-to-end with synthetic events.
- **Phase 8: Docker** — `Dockerfile` (API, non-root user, health check) and `Dockerfile.dashboard` for the Streamlit UI.
- **Phase 8: docker-compose** — `docker-compose.yml` (production, API healthcheck gates dashboard start), `docker-compose.dev.yml` (source-mount live reload).
- **Phase 8: GitHub Actions CI** — tests across Python 3.10, 3.11, 3.12; ruff lint; Docker build verification.
- **Phase 8: Test suite** — 50+ tests across 6 modules covering all phases. All tests use in-memory stores; no disk state shared between tests.
