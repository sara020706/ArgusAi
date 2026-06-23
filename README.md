# 👁️ Argus

**AI-powered insider threat and anomalous user behavior detection — pip-installable, API-first, dashboard included.**

![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-brightgreen)

---

## What is Argus?

Argus is a self-contained UEBA (User and Entity Behaviour Analytics) engine that assigns a 0–100 risk score to every user activity event. It learns each user's normal behaviour over time and flags deviations — unusual login times, large data transfers, unknown devices, escalating download patterns — with human-readable explanations. It ships as a Python package, a REST API, and a Streamlit SOC dashboard, all with zero mandatory cloud dependencies.

Security teams integrate Argus into existing applications in minutes: import the package, POST to the API, or deploy the full stack with one Docker command. The scoring pipeline combines deterministic rules, statistical baselines, an optional ML layer (scikit-learn IsolationForest), IP threat intelligence (AbuseIPDB), and a multi-event correlation engine — all independently configurable.

---

## How it works

**The scenario:** John normally logs in from the office between 9 AM and 6 PM, downloads about 50 MB per session, and accesses around 20 files. One night at 2:15 AM he connects from an unrecognized IP in Eastern Europe, downloads 5 GB, and touches 600 files.

Argus scores that event instantly:

```
+-------------------------------------+
|  ARGUS THREAT ASSESSMENT            |
|  User: john                         |
|  Time: 2026-06-16 02:15:00          |
|  Risk Score: 100/100 [CRITICAL]     |
+-------------------------------------+

Contributing Factors:
  #1 (+50 pts) Large download: 5000 MB (threshold: 1000 MB)
  #2 (+35 pts) Login during night hours (00:00-05:00)
  #3 (+25 pts) Excessive file access: 600 files
  #4 (+20 pts) Login from unrecognized IP address
  #5 (+20 pts) Login from unrecognized device

Recommended Action: Escalate to security team - possible active threat
```

---

## Quick start

### Path A — Python package

```bash
pip install argus
```

```python
from datetime import datetime
from argus import ArgusEngine, Event
from argus.storage import MemoryStore
from argus.explainer import build_explanation

engine = ArgusEngine(store=MemoryStore())

event = Event(
    user_id="john",
    timestamp=datetime(2026, 6, 16, 2, 15),
    ip="185.45.67.10",
    device_id="unknown-device-44",
    download_mb=5000,
    files_accessed=600,
    action="download",
)

result = engine.score(event)
print(build_explanation(result))
# → prints the CRITICAL explanation block above
```

### Path B — REST API server

```bash
pip install "argus[api]"
argus-serve --port 8000
```

```bash
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

Interactive API docs: http://localhost:8000/docs

### Path C — Full stack with Docker

```bash
git clone https://github.com/yourname/argus
cd argus
cp .env.example .env
docker-compose up
```

- **API** → http://localhost:8000
- **API docs** → http://localhost:8000/docs
- **Dashboard** → http://localhost:8501

---

## Installation options

| Command | Adds |
|---|---|
| `pip install argus` | Core engine only — zero dependencies |
| `pip install "argus[api]"` | FastAPI REST server + uvicorn |
| `pip install "argus[ml]"` | IsolationForest anomaly detector (scikit-learn) |
| `pip install "argus[dashboard]"` | Streamlit SOC dashboard + Plotly |
| `pip install "argus[network]"` | Live network capture (pyshark) |
| `pip install "argus[files]"` | Live file monitoring (watchdog) |
| `pip install "argus[all]"` | Everything above |
| `pip install "argus[dev]"` | Test suite + ruff linter |

---

## Architecture overview

See [docs/architecture.md](docs/architecture.md) for full detail.

```
Data Sources → Collectors → ArgusEngine → Storage
                                 │
                           API Server ← Dashboard
```

```
Event
  │
  ├─ 1. Feature Extraction   (hour, weekend, cyclic encoding, z-scores)
  ├─ 2. Heuristic Rules      (7 rules, up to 35 pts each)
  ├─ 3. Statistical Baseline (Welford mean/std, z-score bands)
  ├─ 4. ML Anomaly Layer     (IsolationForest, optional, +0-20 pts)
  ├─ 5. Threat Intelligence  (AbuseIPDB, optional, +0-40 pts)
  └─ 6. Correlation Engine   (5 attack patterns, +20-40 pts each)
        │
        ▼
  ScoreResult (0-100) → build_explanation() → human-readable report
```

---

## Scoring explained

Each event is scored by three independent layers that add up:

| Layer | Max contribution | Requires |
|---|---|---|
| Heuristic rules | ~160 pts (capped at 100) | nothing |
| Statistical deviation | +30 pts | ≥20 events of history |
| ML anomaly | +20 pts | scikit-learn installed + model trained |
| Threat intelligence | +40 pts | AbuseIPDB API key |
| Correlation patterns | +40 pts per pattern | recent event history |

**Risk bands:**

| Score | Level | Action |
|---|---|---|
| 0–30 | LOW | Monitor — no immediate action |
| 31–60 | MEDIUM | Review last 24 hours of activity |
| 61–85 | HIGH | Investigate immediately |
| 86–100 | CRITICAL | Escalate to security team |

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/events/score` | Score a single event |
| `POST` | `/v1/events/batch` | Score up to 100 events in one call |
| `GET` | `/v1/alerts` | Recent alerts (filterable by level, limit) |
| `GET` | `/v1/alerts/stats` | Today's alert counts by level |
| `GET` | `/v1/users/{id}/profile` | User's behavioural baseline |
| `GET` | `/v1/users/{id}/events` | User's recent scored events |
| `GET` | `/v1/users/{id}/risk_summary` | Risk trend and summary |
| `GET` | `/health` | Server health (always 200) |
| `GET` | `/metrics` | Total events, users, avg score |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ARGUS_DB_PATH` | `argus.db` | SQLite database path |
| `ARGUS_PORT` | `8000` | API server port |
| `DASHBOARD_PORT` | `8501` | Dashboard port |
| `ARGUS_API_KEY` | _(unset)_ | Require `X-API-Key` header on all requests |
| `ABUSEIPDB_KEY` | _(unset)_ | Enable IP threat intelligence layer |
| `ARGUS_ENABLE_ML` | `false` | Train and enable IsolationForest on startup |
| `ARGUS_API_URL` | `http://localhost:8000` | Dashboard → API URL |

---

## Running tests

```bash
pip install -e ".[ml,api,dev]"

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=argus --cov-report=html

# Lint
ruff check argus/
```

---

## Project structure

```
argus/
├── argus/                         # Python package
│   ├── __init__.py                # Public API: Event, ScoreResult, ArgusEngine, score()
│   ├── schema.py                  # Event and ScoreResult dataclasses
│   ├── features.py                # Pure feature extraction functions
│   ├── rules.py                   # 7 heuristic rules → (points, reason)
│   ├── statistics.py              # Welford z-score statistical layer
│   ├── scorer.py                  # compute_score() — ties layers together
│   ├── explainer.py               # build_explanation(), summarize_result()
│   ├── profile.py                 # UserProfile with Welford online updates
│   ├── detectors.py               # IsolationForestDetector (sklearn optional)
│   ├── correlator.py              # Multi-event attack pattern detection
│   ├── storage/
│   │   ├── base.py                # ArgusStore abstract base class
│   │   ├── sqlite_store.py        # SQLite backend (stdlib sqlite3)
│   │   └── memory_store.py        # In-memory backend for tests
│   ├── integrations/
│   │   └── threat_intel.py        # AbuseIPDB client (stdlib urllib)
│   ├── synthetic/
│   │   └── generator.py           # Synthetic event and dataset generation
│   ├── collectors/
│   │   ├── base.py                # BaseCollector ABC
│   │   ├── normalize.py           # Shared normalization helpers
│   │   ├── auth_collector.py      # Linux auth.log / CSV / JSONL reader
│   │   ├── network_collector.py   # NetFlow CSV / traffic log reader
│   │   ├── file_collector.py      # auditd / CSV file-access reader
│   │   └── simulate.py            # Generate synthetic log files for demos
│   ├── api/
│   │   ├── server.py              # FastAPI app factory + uvicorn runner
│   │   ├── dependencies.py        # Shared engine singleton
│   │   ├── middleware.py          # Optional API-key authentication
│   │   └── routes/                # events, alerts, users, health endpoints
│   └── dashboard/
│       ├── app.py                 # Streamlit entry point
│       ├── api_client.py          # 9 typed API helper functions
│       ├── components/            # risk_badge, charts (Plotly)
│       └── pages/                 # Alerts, User Profiles, Threat Map
├── tests/                         # pytest test suite (6 modules, 50+ tests)
├── docs/
│   └── architecture.md            # Full architecture and integration guide
├── Dockerfile                     # API server image (non-root, healthcheck)
├── Dockerfile.dashboard           # Dashboard image
├── docker-compose.yml             # Production stack
├── docker-compose.dev.yml         # Development stack (source mount, reload)
├── .env.example                   # Environment variable template
├── .github/workflows/ci.yml       # CI: test 3.10/3.11/3.12, lint, Docker build
├── pyproject.toml                 # PEP 517 build config + optional extras
├── CHANGELOG.md                   # Release history
└── CONTRIBUTING.md                # Developer guide
```

---

## Roadmap

- [ ] PostgreSQL storage adapter
- [ ] Autoencoder detector (TensorFlow / ONNX)
- [ ] LDAP / Active Directory user resolution
- [ ] Slack and PagerDuty alert webhooks
- [ ] MITRE ATT&CK technique tagging on pattern matches
- [ ] Node.js package (ONNX inference, zero Python dependency)
- [ ] Time-series anomaly on login frequency (ARIMA)
- [ ] Multi-tenant support with per-tenant baselines

---

## License

MIT
