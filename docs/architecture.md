# Argus Architecture

## 1. Overview

Argus is a pip-installable Python library and REST API for detecting insider threats and anomalous user behaviour in real time. It is designed for security operations teams and application developers who need a programmable, self-contained UEBA (User and Entity Behaviour Analytics) engine without a cloud dependency. Any application can import Argus directly, integrate via REST, or deploy the full stack with a single `docker-compose up`.

## 2. System Architecture Diagram

```
╔══════════════════════════════════════════════════════════════╗
║                        DATA SOURCES                          ║
║  /var/log/auth.log   NetFlow CSV   audit.log   Custom app    ║
╚══════════════╤═══════════════╤═══════════════╤══════════════╝
               │               │               │
    ┌──────────▼──────┐ ┌──────▼──────┐ ┌─────▼──────────┐
    │  AuthCollector  │ │NetworkColl. │ │  FileCollector │
    │  (Phase 7)      │ │  (Phase 7)  │ │   (Phase 7)    │
    └──────────┬──────┘ └──────┬──────┘ └─────┬──────────┘
               │               │               │
               └───────────────┴───────────────┘
                               │  argus.Event
               ┌───────────────▼───────────────┐
               │         ArgusEngine            │
               │  ┌─────────────────────────┐  │
               │  │  1. Feature Extraction  │  │
               │  │  2. Heuristic Rules     │  │
               │  │  3. Statistical Baseline│  │
               │  │  4. ML Anomaly Layer    │  │
               │  │  5. Threat Intelligence │  │
               │  │  6. Correlation Engine  │  │
               │  └────────────┬────────────┘  │
               │               │ ScoreResult   │
               └───────────────┼───────────────┘
                               │
               ┌───────────────▼───────────────┐
               │         ArgusStore             │
               │   SQLiteStore / MemoryStore    │
               │   (or custom implementation)   │
               └───────────────┬───────────────┘
                               │
               ┌───────────────▼───────────────┐
               │       FastAPI REST Server      │  ← API docs: /docs
               │   POST /v1/events/score        │
               │   POST /v1/events/batch        │
               │   GET  /v1/alerts              │
               │   GET  /v1/users/{id}/profile  │
               │   GET  /health  GET /metrics   │
               └───────────────┬───────────────┘
                               │ HTTP (JSON)
               ┌───────────────▼───────────────┐
               │     Streamlit Dashboard        │
               │  Overview · Alerts · Profiles  │
               └───────────────────────────────┘
```

## 3. Scoring Pipeline

One event becomes a risk score through six sequential layers:

```
Event (user_id, timestamp, ip, device_id, download_mb, files_accessed, action)
  │
  ▼
1. Feature Extraction (argus/features.py)
   • Temporal: hour, is_night_access, is_off_hours, is_weekend, cyclic sin/cos
   • Volume:   download_mb, files_accessed, download_zscore, files_zscore
   • Identity: is_new_ip, is_new_device
  │
  ▼
2. Heuristic Rules (argus/rules.py)
   • rule_night_access    +35 pts  (00:00-05:59)
   • rule_off_hours       +20 pts  (before 09 / after 18, suppressed if night)
   • rule_weekend_access  +10 pts
   • rule_large_download  +30-50 pts (scales from 1 GB to 5 GB)
   • rule_excessive_files +25 pts  (> 100 files)
   • rule_new_ip          +20 pts
   • rule_new_device      +20 pts
  │
  ▼
3. Statistical Baseline (argus/statistics.py)
   • z-score bands: z<1.5 → 0, z<2 → 0.5×weight, z<3 → 1×weight, z≥3 → 2×weight
   • stat_download_deviation   weight=15
   • stat_file_access_deviation weight=10
  │
  ▼
4. ML Anomaly Layer (argus/detectors.py) [optional, requires sklearn]
   • IsolationForest trained on synthetic normal behaviour
   • Contributes 0-20 additional points
  │
  ▼
5. Threat Intelligence (argus/integrations/threat_intel.py) [optional, requires API key]
   • AbuseIPDB lookup (private IPs never sent)
   • 0-40 additional points based on confidence score
  │
  ▼
6. Correlation Engine (argus/correlator.py)
   • Slides a 24-hour window over recent events
   • Detects: repeated_night_logins, escalating_downloads, reconnaissance,
              slow_exfiltration, account_takeover_indicators
   • 20-40 bonus points per detected pattern (total capped at 100)
  │
  ▼
ScoreResult → build_explanation() → human-readable ASCII report
```

**Risk Bands:**

| Score | Level    | Recommended Action                              |
|-------|----------|-------------------------------------------------|
| 0-30  | LOW      | Monitor — no immediate action required          |
| 31-60 | MEDIUM   | Review user activity for the past 24 hours      |
| 61-85 | HIGH     | Investigate immediately, consider termination   |
| 86-100| CRITICAL | Escalate to security team — possible active threat |

## 4. Storage Architecture

All persistence is abstracted behind `ArgusStore` (`argus/storage/base.py`), an abstract base class with five methods:

| Method | Description |
|---|---|
| `get_profile(user_id)` | Load a user's behavioural baseline |
| `save_profile(user_id, data)` | Persist an updated baseline |
| `log_event(event, result)` | Store a scored event for alerting and correlation |
| `get_recent_alerts(limit, min_risk_level)` | Query recent high-risk events |
| `get_user_events(user_id, limit)` | Load a user's event history for correlation |

Two built-in backends:

- **`SQLiteStore`** — default backend using stdlib `sqlite3`. Tables: `user_profiles` (JSON blob per user) and `scored_events` (one row per event). Thread-safe (`check_same_thread=False`).
- **`MemoryStore`** — dict-backed in-process store for unit tests and lightweight deployments. No persistence across restarts.

To use your own database, subclass `ArgusStore` and pass it to `ArgusEngine`:

```python
from argus.storage import ArgusStore

class PostgresStore(ArgusStore):
    def get_profile(self, user_id): ...
    def save_profile(self, user_id, data): ...
    def log_event(self, event, result): ...
    def get_recent_alerts(self, limit, min_risk_level): ...
    def get_user_events(self, user_id, limit): ...

engine = ArgusEngine(store=PostgresStore(dsn="..."))
```

## 5. Module Reference

| Module | File | Purpose | Key symbols |
|---|---|---|---|
| Schema | `argus/schema.py` | Core data classes | `Event`, `ScoreResult` |
| Features | `argus/features.py` | Feature extraction | `build_feature_vector`, `cyclic_encode_hour` |
| Rules | `argus/rules.py` | Heuristic rules | `evaluate_all_rules`, `rule_*` functions |
| Statistics | `argus/statistics.py` | Statistical deviation | `evaluate_all_stats`, `zscore_contribution` |
| Scorer | `argus/scorer.py` | Score assembly | `compute_score`, `get_risk_level`, `cap_score` |
| Explainer | `argus/explainer.py` | Human-readable output | `build_explanation`, `summarize_result` |
| Profile | `argus/profile.py` | Welford baseline | `UserProfile`, `update`, `as_scoring_profile` |
| Storage | `argus/storage/` | Persistence ABC + backends | `ArgusStore`, `SQLiteStore`, `MemoryStore` |
| Detectors | `argus/detectors.py` | ML anomaly detection | `IsolationForestDetector` |
| Correlator | `argus/correlator.py` | Multi-event patterns | `correlate`, `compute_window_stats` |
| Threat Intel | `argus/integrations/threat_intel.py` | IP reputation | `ThreatIntelClient` |
| Synthetic | `argus/synthetic/generator.py` | Test data generation | `generate_dataset`, `events_to_feature_matrix` |
| API Server | `argus/api/server.py` | FastAPI app | `create_app`, `run` |
| Collectors | `argus/collectors/` | Real-world data ingestion | `AuthCollector`, `NetworkCollector`, `FileCollector` |
| Simulation | `argus/collectors/simulate.py` | Demo/test log files | `run_simulation`, `simulate_auth_log` |
| Dashboard | `argus/dashboard/` | Streamlit SOC UI | `app.main` |

## 6. Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `ARGUS_DB_PATH` | `argus.db` | SQLite database file path |
| `ARGUS_PORT` | `8000` | API server port |
| `DASHBOARD_PORT` | `8501` | Streamlit dashboard port |
| `ARGUS_API_KEY` | _(unset)_ | If set, all API requests require `X-API-Key` header |
| `ABUSEIPDB_KEY` | _(unset)_ | AbuseIPDB API key for threat intelligence layer |
| `ARGUS_ENABLE_ML` | `false` | Train and enable IsolationForest on startup |
| `ARGUS_API_URL` | `http://localhost:8000` | Dashboard → API URL (dashboard only) |

## 7. Integration Patterns

### Pattern A — Direct Python import

The simplest integration. Import `ArgusEngine` and call `score()` inline.

```python
from argus import ArgusEngine, Event
from argus.storage import SQLiteStore
from argus.explainer import build_explanation
from datetime import datetime

engine = ArgusEngine(store=SQLiteStore("argus.db"))

event = Event(
    user_id="john",
    timestamp=datetime.now(),
    ip="192.168.1.10",
    device_id="laptop-01",
    download_mb=50.0,
    files_accessed=12,
    action="login",
)

result = engine.score(event)
if result.risk_level in ("HIGH", "CRITICAL"):
    print(build_explanation(result))
    # → alert your SIEM / send a Slack message / page on-call
```

### Pattern B — Watch mode (continuous collection)

Run a collector in a background thread; it calls your callback for every new event.

```python
import threading
from argus import ArgusEngine
from argus.storage import SQLiteStore
from argus.collectors import AuthCollector

engine = ArgusEngine(store=SQLiteStore("argus.db"))
collector = AuthCollector("/var/log/auth.log")

thread = threading.Thread(
    target=collector.watch_and_score,
    args=(engine,),
    kwargs={"interval_seconds": 5.0},
    daemon=True,
)
thread.start()
```

### Pattern C — REST API integration

Deploy the API server and POST events from any language.

```bash
# Start the server
pip install argus[api]
argus-serve --port 8000

# Score an event (any language)
curl -X POST http://localhost:8000/v1/events/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john",
    "timestamp": "2026-06-16T02:15:00",
    "ip": "185.45.67.10",
    "device_id": "unknown-device-44",
    "download_mb": 5000,
    "files_accessed": 600,
    "action": "download"
  }'
```

Response:

```json
{
  "user_id": "john",
  "risk_score": 100.0,
  "risk_level": "CRITICAL",
  "explanation": "+-------------------------------------+\n|  ARGUS THREAT ASSESSMENT  ...",
  "reasons": ["Login during night hours (00:00-05:00)", "Large download: 5000 MB"]
}
```
