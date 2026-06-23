# Argus — Setup & User Manual
**AI-Powered Insider Threat Detection**
*Version 0.1.0*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Project Structure](#3-project-structure)
4. [Installation](#4-installation)
5. [Running Argus](#5-running-argus)
6. [Verifying the Installation](#6-verifying-the-installation)
7. [Using the API](#7-using-the-api)
8. [Using the Dashboard](#8-using-the-dashboard)
9. [Using the Python Package Directly](#9-using-the-python-package-directly)
10. [Configuring a Different Database](#10-configuring-a-different-database)
11. [Enabling ML (Isolation Forest)](#11-enabling-ml-isolation-forest)
12. [Enabling Threat Intelligence](#12-enabling-threat-intelligence)
13. [Running Tests](#13-running-tests)
14. [Understanding Risk Scores](#14-understanding-risk-scores)
15. [Troubleshooting](#15-troubleshooting)
16. [Quick Reference Card](#16-quick-reference-card)

---

## 1. Introduction

Argus AI is an open-source, AI-powered insider threat and anomalous user behavior detection package built in Python. It learns each user's behavioral baseline — login hours, download volumes, devices, IP addresses — and scores every event against that baseline in milliseconds, returning a 0–100 risk score with a plain-language explanation of every contributing factor.

This manual covers installation, configuration, running all services (API, dashboard, demo website), using the REST API, understanding risk scores, enabling optional ML and threat intelligence layers, and troubleshooting common issues.

---

## 2. System Requirements

This section lists the minimum and recommended hardware and software requirements to run Argus.

| Component | Minimum | Recommended |
|---|---|---|
| Python | 3.10 | 3.11 or 3.12 |
| RAM | 512 MB | 2 GB |
| Disk | 200 MB | 1 GB |
| OS | Windows / macOS / Linux | Any |
| Node.js (demo website only) | 18.x | 20.x |
| Docker (optional) | 24.x | Latest |

---

## 3. Project Structure

This section shows the full directory layout with a one-line description of every file and folder.

```
argus/
├── argus/                          ← Python package source
│   ├── __init__.py                 ← public API entry point (score, ArgusEngine)
│   ├── schema.py                   ← Event and ScoreResult dataclasses
│   ├── features.py                 ← feature extraction (13 features per event)
│   ├── rules.py                    ← rule engine — 7 hard rules with point weights
│   ├── statistics.py               ← z-score deviation scoring per user baseline
│   ├── scorer.py                   ← combines all layers into a 0–100 risk score
│   ├── explainer.py                ← builds human-readable explanation of each score
│   ├── profile.py                  ← UserProfile with Welford online baseline tracking
│   ├── detectors.py                ← Isolation Forest ML anomaly detector (optional)
│   ├── correlator.py               ← multi-event attack pattern engine (24 h window)
│   ├── storage/                    ← pluggable storage layer
│   │   ├── base.py                 ← ArgusStore abstract base class
│   │   ├── sqlite_store.py         ← default SQLite backend (stdlib, no extra deps)
│   │   └── memory_store.py         ← in-memory backend for testing
│   ├── integrations/               ← external service connectors
│   │   └── threat_intel.py         ← AbuseIPDB IP reputation lookup with caching
│   ├── api/                        ← FastAPI REST server
│   │   ├── server.py               ← app factory + argus-serve CLI entry point
│   │   ├── dependencies.py         ← shared engine instance + initialize_engine()
│   │   ├── middleware.py           ← optional API key auth middleware
│   │   └── routes/                 ← endpoint handlers (events, alerts, users, health)
│   ├── dashboard/                  ← Streamlit SOC visual dashboard
│   │   ├── app.py                  ← entry point + argus-dashboard CLI
│   │   ├── api_client.py           ← HTTP client wrapping the Argus REST API
│   │   ├── components/             ← reusable Streamlit UI widgets
│   │   └── pages/                  ← Overview, Alerts, User Profiles, Threat Map
│   ├── collectors/                 ← data source bridges
│   │   ├── auth_collector.py       ← reads syslog/SSH auth logs
│   │   ├── network_collector.py    ← reads network traffic logs
│   │   ├── file_collector.py       ← reads file access audit logs
│   │   ├── normalize.py            ← shared field normalization helpers
│   │   └── simulate.py             ← generates synthetic log files for testing
│   └── synthetic/                  ← ML training data generator
│       └── generator.py            ← creates realistic user event datasets
├── website/                        ← React + Vite landing page (inside argus repo)
├── tests/                          ← pytest test suite — 81 tests across 6 files
├── docs/                           ← documentation (architecture, changelog, this file)
├── Dockerfile                      ← multi-stage image for API server (non-root uid 1000)
├── Dockerfile.dashboard            ← multi-stage image for Streamlit dashboard
├── docker-compose.yml              ← production stack with health-check dependency
├── docker-compose.dev.yml          ← development stack with volume mounts + hot reload
├── pyproject.toml                  ← package metadata, optional deps, tool config
├── start.bat                       ← Windows one-click launcher (API + dashboard)
├── start-all.bat                   ← Windows launcher (API + dashboard + React website)
├── .env.example                    ← environment variable template (no real keys)
└── argus.db                        ← SQLite database file (auto-created on first run)
```

---

## 4. Installation

This section covers all methods for installing Argus and its dependencies.

### 4.1 Clone or Download the Project

**Via Git (recommended):**

```bash
git clone https://github.com/yourname/argus.git
cd argus
```

**Manual download:**

Download the ZIP from GitHub → Extract → `cd` into the extracted folder.

### 4.2 Install Python Dependencies

All installation options use `pip install -e` (editable install) so changes to source files take effect immediately without reinstalling.

| Command | What it installs |
|---|---|
| `pip install -e "."` | Core package only — no API, no dashboard |
| `pip install -e ".[api]"` | Core + FastAPI REST server |
| `pip install -e ".[dashboard]"` | Core + Streamlit dashboard |
| `pip install -e ".[ml]"` | Core + scikit-learn Isolation Forest |
| `pip install -e ".[api,dashboard]"` | API + Dashboard (recommended for most users) |
| `pip install -e ".[api,dashboard,ml]"` | API + Dashboard + ML (recommended first-time) |
| `pip install -e ".[all]"` | Everything including network and file collectors |

**First-time recommended install:**

```bash
pip install -e ".[api,dashboard,ml]"
```

### 4.3 Configure Environment Variables

Copy the example file and edit it:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and configure as needed:

| Variable | Default | Description |
|---|---|---|
| `ARGUS_PORT` | `8000` | Port the API server listens on |
| `DASHBOARD_PORT` | `8501` | Port the Streamlit dashboard listens on |
| `ARGUS_API_KEY` | *(empty)* | Optional API authentication key — leave empty to disable auth |
| `ABUSEIPDB_KEY` | *(empty)* | AbuseIPDB threat intelligence API key — leave empty to disable |
| `ARGUS_ENABLE_ML` | `false` | Set to `true` to enable Isolation Forest anomaly detection |
| `ARGUS_DB_PATH` | `argus.db` | Path to the SQLite database file |
| `ARGUS_API_URL` | `http://localhost:8000` | Used by dashboard and demo website to reach the API |

### 4.4 Install Node.js Dependencies (Demo Website Only)

The React demo website lives in `website/` inside the argus repo.

```bash
cd website
npm install
```

Requires Node.js 18 or higher. Check with `node --version`.

---

## 5. Running Argus

This section covers all four ways to start Argus.

### 5.1 Option 1: One-Click (Windows)

Double-click **`start.bat`** in the project root. It handles everything automatically:

1. Verifies Python is available at the configured path
2. Starts the API server in a new console window
3. Polls `http://localhost:8000/health` every second for up to 20 seconds
4. Starts the Streamlit dashboard once the API is confirmed healthy
5. Opens the dashboard in your default browser

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

To start all three services including the React website, double-click **`start-all.bat`** instead. It also auto-runs `npm install` in `website/` on first run.

### 5.2 Option 2: Manual (Two Terminals)

**Terminal 1 — API server:**

```bash
cd path/to/argus
python -m uvicorn argus.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

**Terminal 2 — Streamlit dashboard:**

```bash
cd path/to/argus
python -m streamlit run argus\dashboard\app.py --server.port 8501
```

On macOS / Linux, use forward slashes: `argus/dashboard/app.py`.

### 5.3 Option 3: Docker (Recommended for Production)

**Prerequisites:** Docker Desktop must be installed and running.

**Production stack:**

```bash
cp .env.example .env
docker-compose up
```

The dashboard container waits for the API health check to pass before starting.

**Development stack (with live reload):**

```bash
docker-compose -f docker-compose.dev.yml up
```

This mounts the source directory into the container so code changes apply instantly without rebuilding.

**Stop everything:**

```bash
docker-compose down
```

### 5.4 Option 4: Demo Website (React)

**Prerequisites:** Node.js 18+, and the Argus API must be running on port 8000.

```bash
cd website
npm install    # first time only
npm run dev
```

Opens at: **http://localhost:3001**

To point the website at a different API URL, create `website/.env.local`:

```
VITE_ARGUS_API_URL=http://your-api-host:8000
```

---

## 6. Verifying the Installation

This section walks through five checks that confirm every part of Argus is working correctly.

### Step 1 — Check API Health

Open in browser: **http://localhost:8000/health**

Expected response:

```json
{
  "status": "healthy",
  "engine_initialized": true,
  "db_connected": true,
  "ml_enabled": false,
  "uptime_seconds": 4.2
}
```

If `engine_initialized` is `false`, the API started but the engine failed to initialise — check the console window for errors.

### Step 2 — Score a Normal Event

Open **http://localhost:8000/docs** → Click `POST /v1/events/score` → **Try it out** → paste:

```json
{
  "user_id": "alice",
  "timestamp": "2026-06-23T09:15:00",
  "ip": "192.168.1.5",
  "device_id": "work-laptop-01",
  "download_mb": 45,
  "files_accessed": 18,
  "action": "login"
}
```

**Expected result:** `risk_level = "LOW"`, `risk_score < 30`

### Step 3 — Score a Suspicious Event

Same endpoint, paste:

```json
{
  "user_id": "john",
  "timestamp": "2026-06-23T02:15:00",
  "ip": "185.45.67.10",
  "device_id": "unknown-device-99",
  "download_mb": 5000,
  "files_accessed": 600,
  "action": "download"
}
```

**Expected result:** `risk_level = "CRITICAL"`, `risk_score > 85`

### Step 4 — Check the Alert Feed

```bash
curl http://localhost:8000/v1/alerts
```

John's CRITICAL event should appear in the list. Alerts are only stored for events that score above the LOW threshold.

### Step 5 — Open the Dashboard

Open **http://localhost:8501** — the Overview page should show an alert count greater than zero, with john's event visible in the recent alerts table.

---

## 7. Using the API

This section covers all REST endpoints, request formats, and authentication.

### 7.1 All Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/events/score` | Score a single event — returns risk score + explanation |
| `POST` | `/v1/events/batch` | Score up to 100 events in one request |
| `GET` | `/v1/alerts` | Get recent alerts (query: `limit`, `min_risk_level`) |
| `GET` | `/v1/alerts/stats` | Alert counts grouped by risk level |
| `GET` | `/v1/users/{id}/profile` | User behavioral profile and baseline stats |
| `GET` | `/v1/users/{id}/events` | Full event history for a user |
| `GET` | `/v1/users/{id}/risk_summary` | Aggregated risk summary for a user |
| `GET` | `/health` | Health check — engine status, uptime |
| `GET` | `/metrics` | System metrics — total events scored, alert counts |

### 7.2 Request and Response Examples

**Score a single event:**

```bash
curl -X POST http://localhost:8000/v1/events/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "timestamp": "2026-06-23T09:15:00",
    "ip": "192.168.1.5",
    "device_id": "work-laptop-01",
    "download_mb": 45,
    "files_accessed": 18,
    "action": "login"
  }'
```

Example response:

```json
{
  "user_id": "alice",
  "timestamp": "2026-06-23T09:15:00",
  "risk_score": 12.0,
  "risk_level": "LOW",
  "rules_fired": [],
  "explanation": "No significant anomalies detected.",
  "contributing_factors": []
}
```

**Get recent alerts:**

```bash
curl "http://localhost:8000/v1/alerts?limit=20&min_risk_level=MEDIUM"
```

Example response:

```json
[
  {
    "user_id": "john",
    "timestamp": "2026-06-23T02:15:00",
    "risk_score": 94.0,
    "risk_level": "CRITICAL",
    "reasons": [
      "Login during night hours (00:00–05:00)",
      "Large download: 5000 MB",
      "Login from unrecognized IP",
      "Login from unrecognized device"
    ]
  }
]
```

**Get alert statistics:**

```bash
curl http://localhost:8000/v1/alerts/stats
```

Example response:

```json
{
  "total": 3,
  "by_level": {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 1,
    "CRITICAL": 1
  }
}
```

**Get a user profile:**

```bash
curl http://localhost:8000/v1/users/alice/profile
```

Example response:

```json
{
  "user_id": "alice",
  "event_count": 24,
  "avg_download_mb": 47.2,
  "std_download_mb": 11.8,
  "avg_files_accessed": 19.4,
  "std_files_accessed": 4.9,
  "known_ips": ["192.168.1.5", "192.168.1.12"],
  "known_devices": ["work-laptop-01"],
  "is_mature": true
}
```

**Get system metrics:**

```bash
curl http://localhost:8000/metrics
```

Example response:

```json
{
  "total_events_scored": 47,
  "total_alerts": 3,
  "uptime_seconds": 182.4,
  "started_at": "2026-06-23T09:00:00"
}
```

### 7.3 API Authentication

If `ARGUS_API_KEY` is set in `.env`, every request must include the key as a header:

```bash
curl -H "X-API-Key: your-key-here" http://localhost:8000/v1/alerts
```

Requests without the key return `403 Forbidden`. Leaving `ARGUS_API_KEY` empty disables authentication entirely (default for local use).

### 7.4 Batch Scoring

Score up to 100 events in a single request:

```bash
curl -X POST http://localhost:8000/v1/events/batch \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "user_id": "alice",
        "timestamp": "2026-06-23T09:15:00",
        "ip": "192.168.1.5",
        "device_id": "work-laptop-01",
        "download_mb": 45,
        "files_accessed": 18,
        "action": "login"
      },
      {
        "user_id": "john",
        "timestamp": "2026-06-23T02:15:00",
        "ip": "185.45.67.10",
        "device_id": "unknown-device-99",
        "download_mb": 5000,
        "files_accessed": 600,
        "action": "download"
      }
    ]
  }'
```

Returns a list of score results in the same order as the input. Sending more than 100 events returns `422 Unprocessable Entity`.

---

## 8. Using the Dashboard

This section describes each page of the Streamlit SOC dashboard.

### 8.1 Overview Page

The Overview page gives a real-time summary of all threat activity across your organisation.

**What it shows:**
- Alert count tiles: total alerts, high-severity count, critical count
- Recent alerts table with colour-coded risk badges
- Alert distribution pie chart by risk level
- Top 5 users by total alert count
- Hourly activity heatmap (hour of day x day of week)

**How to use it:**
- Use the **Refresh** button to pull the latest data from the API
- The heatmap highlights unusual hours in amber/red — a bright cell at 02:00–04:00 is always worth investigating
- Click any row in the alerts table to jump to that user's profile

### 8.2 Live Alerts Page

The Live Alerts page shows a filterable, real-time alert feed updated every few seconds.

**What it shows:**
- All alerts above the selected minimum risk level
- Each card shows: user ID, risk badge, top reason, score, and timestamp
- Expandable cards reveal the full list of contributing factors

**How to use it:**
- Use the **Risk Level** multiselect to filter to HIGH and CRITICAL only
- Use the **User ID** search box to focus on a specific user
- Click any alert card to expand and see all contributing factors with point breakdowns
- The feed auto-refreshes — new alerts slide in at the top

### 8.3 User Profiles Page

The User Profiles page shows the behavioral baseline Argus has learned for each user.

**What it shows:**
- Search box to look up any user by ID
- **Behavioral Profile tab:** average and standard deviation for download size and files accessed; list of known IPs and devices; event count; profile maturity indicator
- **Activity Timeline tab:** chart of all scored events over time, coloured by risk level
- **Risk Summary tab:** breakdown of risk level distribution for that user

**Profile Mature indicator:**
A profile is marked **Mature** once Argus has seen 20 or more events for that user. Before 20 events, the statistical z-score layer has insufficient data and contributes less to the score. This is expected behaviour — scores become more accurate as the baseline grows.

### 8.4 Threat Map Page

The Threat Map page shows the geographic origin of flagged login attempts.

**What it shows:**
- World map with a marker for each alert origin IP
- Marker **size** indicates the risk score (larger = higher score)
- Marker **colour** indicates the risk level (green LOW → purple CRITICAL)
- Hover tooltip shows: user ID, risk level, score, city

**Demo mode vs Live mode:**
- When the API is unreachable, the map shows pre-seeded demo points
- When the API is live, markers update every 15 seconds with real alert data
- A banner at the top of the section indicates which mode is active

---

## 9. Using the Python Package Directly

This section shows how to use Argus as a library without running the API server.

### 9.1 Basic Usage

```python
from argus import ArgusEngine
from argus.schema import Event
from datetime import datetime

engine = ArgusEngine()
result = engine.score(Event(
    user_id="alice",
    timestamp=datetime(2026, 6, 23, 9, 15, 0),
    ip="192.168.1.5",
    device_id="work-laptop-01",
    download_mb=45,
    files_accessed=18,
    action="login",
))
print(result.risk_score, result.risk_level)
```

### 9.2 Full Example with Explanation Output

```python
from argus import ArgusEngine
from argus.schema import Event
from argus.explainer import build_explanation
from datetime import datetime

engine = ArgusEngine()

# Normal event
normal = Event(
    user_id="alice",
    timestamp=datetime(2026, 6, 23, 9, 15, 0),
    ip="192.168.1.5",
    device_id="work-laptop-01",
    download_mb=45,
    files_accessed=18,
    action="login",
)

# Suspicious event
suspicious = Event(
    user_id="john",
    timestamp=datetime(2026, 6, 23, 2, 15, 0),
    ip="185.45.67.10",
    device_id="unknown-device-99",
    download_mb=5000,
    files_accessed=600,
    action="download",
)

for event in [normal, suspicious]:
    result = engine.score(event)
    print(build_explanation(result))
    print()
```

**Expected output for the suspicious event:**

```
+-------------------------------------+
|  ARGUS AI THREAT ASSESSMENT         |
|  User:  john
|  Time:  2026-06-23 02:15:00
|  Score: 94/100  [CRITICAL]
+-------------------------------------+

Contributing Factors:
  #1 (+35 pts) Login during night hours (00:00–05:00)
  #2 (+30 pts) Large download: 5000 MB
  #3 (+20 pts) Login from unrecognized IP
  #4 (+20 pts) Login from unrecognized device

Recommended Action:
  Escalate to security team — possible active threat
```

### 9.3 Using Collectors to Read Real Logs

**Pattern A — Direct (read once):**

```python
from argus import ArgusEngine
from argus.collectors import AuthCollector

engine = ArgusEngine()
collector = AuthCollector("/var/log/auth.log")

for event in collector.collect():
    result = engine.score(event)
    if result.risk_level in ("HIGH", "CRITICAL"):
        print(f"ALERT: {result.user_id} scored {result.risk_score}")
```

**Pattern B — Watch mode (continuous, incremental):**

```python
# Polls the log file every second and scores only new lines
collector.watch_and_score(engine, interval_seconds=1.0)
```

**Pattern C — Via API (any language or tool):**

```bash
curl -X POST http://localhost:8000/v1/events/score \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","timestamp":"2026-06-23T09:15:00",
       "ip":"192.168.1.5","device_id":"laptop","download_mb":45,
       "files_accessed":18,"action":"login"}'
```

### 9.4 Running a Simulation (No Real Logs Needed)

```python
from argus import ArgusEngine
from argus.collectors import run_simulation

engine = ArgusEngine()

# Generate 30 days of synthetic activity for 10 users
# Includes realistic anomalies at a 5% rate
results = run_simulation(engine, n_users=10, days=30, print_alerts=True)

print(f"Scored {len(results)} events")
alerts = [r for r in results if r["risk_level"] in ("HIGH", "CRITICAL")]
print(f"Found {len(alerts)} high/critical alerts")
```

---

## 10. Configuring a Different Database

This section explains how to swap the default SQLite backend for any other database.

### 10.1 How the Storage Interface Works

Every Argus component that reads or writes data goes through a single `ArgusStore` interface. The interface requires six operations:

| Method | What it must do |
|---|---|
| `get_profile(user_id)` | Return a `UserProfile` dict or `None` if user is new |
| `save_profile(user_id, profile)` | Persist an updated `UserProfile` |
| `log_event(result)` | Persist a `ScoreResult` (only if score is above LOW threshold) |
| `get_recent_alerts(limit, min_risk_level)` | Return a list of recent alert dicts |
| `get_user_events(user_id, limit)` | Return a list of event dicts for one user |
| `get_stats()` | Return a dict with `total_events_scored` and `total_alerts` |

As long as your backend implements these six methods, Argus will use it exactly as it uses SQLite.

### 10.2 Using Built-in SQLite (Default)

```python
from argus import ArgusEngine
from argus.storage import SQLiteStore

# Default — creates argus.db in the current directory
engine = ArgusEngine()

# Custom path
engine = ArgusEngine(store=SQLiteStore("data/production.db"))
```

### 10.3 PostgreSQL Adapter

```bash
pip install psycopg2-binary
```

```python
import psycopg2
import json
from argus.storage.base import ArgusStore
from argus.profile import UserProfile

class PostgresStore(ArgusStore):
    def __init__(self, dsn: str):
        self.conn = psycopg2.connect(dsn)
        self._create_tables()

    def _create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS argus_profiles (
                    user_id TEXT PRIMARY KEY,
                    data    JSONB NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS argus_events (
                    id         SERIAL PRIMARY KEY,
                    user_id    TEXT NOT NULL,
                    timestamp  TIMESTAMPTZ NOT NULL,
                    risk_score FLOAT NOT NULL,
                    risk_level TEXT NOT NULL,
                    reasons    JSONB NOT NULL DEFAULT '[]'
                )
            """)
            self.conn.commit()

    def get_profile(self, user_id: str):
        with self.conn.cursor() as cur:
            cur.execute("SELECT data FROM argus_profiles WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return UserProfile(**row[0]) if row else None

    def save_profile(self, user_id: str, profile):
        data = profile.__dict__ if hasattr(profile, '__dict__') else profile
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO argus_profiles (user_id, data) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET data = EXCLUDED.data
            """, (user_id, json.dumps(data)))
            self.conn.commit()

    def log_event(self, result):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO argus_events (user_id, timestamp, risk_score, risk_level, reasons)
                VALUES (%s, %s, %s, %s, %s)
            """, (result.user_id, result.timestamp, result.risk_score,
                  result.risk_level, json.dumps(result.reasons)))
            self.conn.commit()

    def get_recent_alerts(self, limit: int = 20, min_risk_level: str = "LOW"):
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, timestamp, risk_score, risk_level, reasons
                FROM argus_events ORDER BY timestamp DESC LIMIT %s
            """, (limit * 4,))
            rows = cur.fetchall()
        return [
            {"user_id": r[0], "timestamp": str(r[1]), "risk_score": r[2],
             "risk_level": r[3], "reasons": r[4]}
            for r in rows
            if order.get(r[3], 0) >= order.get(min_risk_level, 0)
        ][:limit]

    def get_user_events(self, user_id: str, limit: int = 50):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, timestamp, risk_score, risk_level, reasons
                FROM argus_events WHERE user_id = %s
                ORDER BY timestamp DESC LIMIT %s
            """, (user_id, limit))
            rows = cur.fetchall()
        return [{"user_id": r[0], "timestamp": str(r[1]), "risk_score": r[2],
                 "risk_level": r[3], "reasons": r[4]} for r in rows]

    def get_stats(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM argus_events")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM argus_events WHERE risk_level != 'LOW'")
            alerts = cur.fetchone()[0]
        return {"total_events_scored": total, "total_alerts": alerts}
```

**Usage:**

```python
from argus import ArgusEngine
store = PostgresStore("postgresql://user:password@localhost:5432/argus_db")
engine = ArgusEngine(store=store)
```

### 10.4 MongoDB Adapter

```bash
pip install pymongo
```

```python
from pymongo import MongoClient
from argus.storage.base import ArgusStore
from argus.profile import UserProfile

RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

class MongoStore(ArgusStore):
    def __init__(self, uri: str = "mongodb://localhost:27017", db: str = "argus"):
        client = MongoClient(uri)
        self.db = client[db]

    def get_profile(self, user_id: str):
        doc = self.db.profiles.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return UserProfile(**{k: v for k, v in doc.items() if k != "user_id"})
        return None

    def save_profile(self, user_id: str, profile):
        data = profile.__dict__ if hasattr(profile, '__dict__') else dict(profile)
        self.db.profiles.replace_one({"user_id": user_id},
                                     {"user_id": user_id, **data}, upsert=True)

    def log_event(self, result):
        self.db.events.insert_one({
            "user_id":    result.user_id,
            "timestamp":  str(result.timestamp),
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "reasons":    result.reasons,
        })

    def get_recent_alerts(self, limit: int = 20, min_risk_level: str = "LOW"):
        min_order = RISK_ORDER.get(min_risk_level, 0)
        docs = list(self.db.events.find().sort("timestamp", -1).limit(limit * 4))
        results = [
            {"user_id": d["user_id"], "timestamp": d["timestamp"],
             "risk_score": d["risk_score"], "risk_level": d["risk_level"],
             "reasons": d.get("reasons", [])}
            for d in docs
            if RISK_ORDER.get(d.get("risk_level", "LOW"), 0) >= min_order
        ]
        return results[:limit]

    def get_user_events(self, user_id: str, limit: int = 50):
        docs = list(self.db.events.find({"user_id": user_id})
                    .sort("timestamp", -1).limit(limit))
        return [{"user_id": d["user_id"], "timestamp": d["timestamp"],
                 "risk_score": d["risk_score"], "risk_level": d["risk_level"],
                 "reasons": d.get("reasons", [])} for d in docs]

    def get_stats(self):
        total  = self.db.events.count_documents({})
        alerts = self.db.events.count_documents({"risk_level": {"$ne": "LOW"}})
        return {"total_events_scored": total, "total_alerts": alerts}
```

**Usage:**

```python
from argus import ArgusEngine
store = MongoStore("mongodb://localhost:27017", db="argus")
engine = ArgusEngine(store=store)
```

### 10.5 Writing Your Own Adapter

1. Create a class that inherits from `ArgusStore`
2. Implement all six abstract methods
3. Pass an instance to `ArgusEngine(store=YourStore())`

**Minimal skeleton:**

```python
from argus.storage.base import ArgusStore

class MyCustomStore(ArgusStore):

    def get_profile(self, user_id: str):
        """Return UserProfile for user_id, or None if no history exists."""
        ...

    def save_profile(self, user_id: str, profile) -> None:
        """Persist the updated UserProfile for user_id."""
        ...

    def log_event(self, result) -> None:
        """Persist a ScoreResult. Only called for events above LOW threshold."""
        ...

    def get_recent_alerts(self, limit: int = 20, min_risk_level: str = "LOW") -> list:
        """Return list of dicts: user_id, timestamp, risk_score, risk_level, reasons."""
        ...

    def get_user_events(self, user_id: str, limit: int = 50) -> list:
        """Return list of event dicts for one user, newest first."""
        ...

    def get_stats(self) -> dict:
        """Return dict with keys: total_events_scored, total_alerts."""
        ...
```

---

## 11. Enabling ML (Isolation Forest)

This section explains how to activate and use the optional machine learning anomaly detection layer.

### 11.1 Install scikit-learn

```bash
pip install "argus[ml]"
# or
pip install scikit-learn>=1.3
```

### 11.2 Train on Synthetic Data (Quickest Start)

```python
from argus import ArgusEngine
from argus.detectors import IsolationForestDetector

detector = IsolationForestDetector()
engine   = ArgusEngine(detector=detector)
engine.train()   # generates synthetic data and trains the model
                 # saves argus_model.pkl automatically
```

### 11.3 Train on Your Own Historical Data

```python
from argus.schema import Event

your_events = [Event(...), Event(...), ...]   # list of historical Event objects
engine.train(events=your_events)
```

Training on real data makes the model aware of your actual user population's normal behaviour.

### 11.4 Load a Previously Trained Model

```python
detector = IsolationForestDetector()
detector.load("argus_model.pkl")
engine = ArgusEngine(detector=detector)
```

### 11.5 What ML Adds vs Not Using It

| Scenario | Without ML | With ML |
|---|---|---|
| Normal weekday login, known IP | 0 pts from ML | 0 pts (model agrees) |
| Unusual pattern not covered by rules | 0 pts | Up to +20 pts |
| Night access + large download | 65–70 pts | 75–85 pts |
| Fully anomalous multi-signal event | 85–94 pts | 94–100 pts |

The ML layer contributes a maximum of **+20 points** to any single event score. It never lowers a score. If the model is not trained or fails to load, the layer returns 0 and scoring continues normally through the remaining layers.

### 11.6 Enable via Environment Variable

Add to `.env`:

```
ARGUS_ENABLE_ML=true
```

When enabled, the API server auto-trains on startup using synthetic data if no saved model is found at `argus_model.pkl`.

---

## 12. Enabling Threat Intelligence

This section explains how to configure AbuseIPDB IP reputation lookups.

### 12.1 What It Does

When enabled, Argus cross-references every previously unseen IP address against the AbuseIPDB database. The result is cached so each unique IP is only looked up once per session. IPs in RFC 1918 private ranges (192.168.x.x, 10.x.x.x, 172.16–31.x.x) and loopback are never sent to the external API.

### 12.2 Get a Free API Key

1. Go to **https://www.abuseipdb.com/register**
2. Create a free account
3. Copy your API key from the dashboard
4. Free tier: 1000 lookups per day

### 12.3 Configure

**Via `.env`:**

```
ABUSEIPDB_KEY=your-api-key-here
```

**Via code:**

```python
from argus import ArgusEngine
from argus.integrations import ThreatIntelClient

intel  = ThreatIntelClient(api_key="your-api-key-here")
engine = ArgusEngine(threat_intel=intel)
```

### 12.4 Risk Score Impact

| AbuseIPDB Confidence Score | Points Added | Reason Shown in Explanation |
|---|---|---|
| 0–25 | +0 | *(no flag)* |
| 26–50 | +15 | IP flagged as suspicious |
| 51–75 | +25 | IP has high abuse reports |
| 76–100 | +40 | IP is known malicious |

---

## 13. Running Tests

This section covers how to run the Argus test suite.

### 13.1 Run All Tests

```bash
pytest tests/ -v
```

### 13.2 Run with Coverage Report

```bash
pytest tests/ --cov=argus --cov-report=html
```

Then open `htmlcov/index.html` in a browser to view the line-by-line coverage report.

### 13.3 Run Specific Phase Tests

```bash
pytest tests/test_phase1_core.py -v        # core scoring engine
pytest tests/test_phase2_storage.py -v     # storage and profiles
pytest tests/test_phase3_ml.py -v          # ML detector
pytest tests/test_phase4_correlation.py -v # correlation patterns
pytest tests/test_phase5_api.py -v         # REST API endpoints
pytest tests/test_phase7_collectors.py -v  # collectors and normalization
```

### 13.4 Test Summary

| File | Tests | What It Covers |
|---|---|---|
| `test_phase1_core.py` | 19 | Feature extraction, rules, scorer, explainer, risk bands |
| `test_phase2_storage.py` | 8 | SQLiteStore, MemoryStore, UserProfile, Welford accuracy |
| `test_phase3_ml.py` | 6 | Synthetic data, Isolation Forest train/predict/save/load |
| `test_phase4_correlation.py` | 11 | All 5 patterns, window stats, bonus cap, error handling |
| `test_phase5_api.py` | 15 | Health, score, batch, alerts, users, metrics endpoints |
| `test_phase7_collectors.py` | 22 | Normalization helpers, all three collectors, simulation |
| **Total** | **81** | |

---

## 14. Understanding Risk Scores

This section explains exactly how Argus produces a 0–100 risk score and what each band means.

### 14.1 Risk Bands

| Score | Level | Meaning | Recommended Action |
|---|---|---|---|
| 0–30 | **LOW** | Normal behaviour — within expected baseline | Log only, no action required |
| 31–60 | **MEDIUM** | Worth reviewing — one or two mild signals | Review within 24 hours |
| 61–85 | **HIGH** | Likely suspicious — multiple risk signals fired | Investigate today |
| 86–100 | **CRITICAL** | Active threat likely — multiple strong signals | Act immediately, escalate to security team |

### 14.2 How Points Are Assigned

| Signal | Points |
|---|---|
| Night access (00:00–05:59) | +35 |
| Off-hours access (before 09:00 or after 18:00) | +20 *(suppressed if night)* |
| Weekend activity | +10 |
| Large download (>1 GB scaled to >5 GB) | +30–50 |
| Excessive file access (>100 files) | +25 |
| Unknown IP address (never seen for this user) | +20 |
| Unknown device (never seen for this user) | +20 |
| Download z-score > 1.5 | +7–30 (by band) |
| File count z-score > 1.5 | +5–20 (by band) |
| ML anomaly score (Isolation Forest) | +0–20 |
| Correlation pattern bonus | +20–40 |
| AbuseIPDB malicious IP | +15–40 |

All contributions are summed, then **capped at 100**. Scores never exceed 100.

### 14.3 Example Walkthrough — How John Scored 94/100

Event: `john`, `2026-06-23 02:15:00`, IP `185.45.67.10`, device `unknown-device-99`, 5000 MB, 600 files.

| Rule | Reason | Points |
|---|---|---|
| `rule_night_access` | 02:15 is between 00:00–05:59 | +35 |
| `rule_off_hours` | *suppressed — night rule already fired* | 0 |
| `rule_large_download` | 5000 MB → maximum scale | +50 |
| `rule_new_ip` | 185.45.67.10 not in john's known IPs | +20 |
| `rule_new_device` | unknown-device-99 not in john's known devices | +20 |
| Statistical layer | Download z-score ~ 4.2 (5000 MB vs avg 47 MB) | +15 |
| **Raw total** | | **140** |
| **Capped at 100** | | **94** *(after partial cap)* |

The final score is 94 — **CRITICAL**.

### 14.4 Why Per-User Baselines Matter

Two users download 500 MB. Alice's baseline is avg 480 MB (z-score ~ 0.1) — no stat penalty. John's baseline is avg 47 MB (z-score ~ 4.2) — +15 pts statistical penalty. Same download, very different signals because the deviation from each user's own normal behaviour is what matters.

---

## 15. Troubleshooting

This section provides fixes for the seven most common problems.

### Problem 1: API Won't Start — "Address Already in Use"

**Symptom:** `ERROR: [Errno 98] Address already in use` or Windows equivalent.

**Fix — Windows:**

```cmd
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

**Fix — macOS / Linux:**

```bash
lsof -i :8000
kill -9 <pid>
```

Then start the API again.

### Problem 2: Dashboard Shows "API Offline"

**Symptom:** Red dot in the navbar, all sections show "No data" or empty states.

**Checklist:**

1. Is the API actually running? Open http://localhost:8000/health in a browser.
2. Check `ARGUS_API_URL` in `.env` — it must match the port the API is running on.
3. Did you start the dashboard *after* the API? The dashboard reads `ARGUS_API_URL` at startup.
4. If using Docker, check that both containers are on the same network: `docker-compose ps`.

### Problem 3: All Events Scoring LOW

**Symptom:** Even obviously suspicious events (02:00 login, 5 GB download) score under 20.

**Causes and fixes:**

- **Profile not mature yet:** Argus needs 20+ events per user before the statistical layer contributes. Seed history with `run_simulation(engine, n_users=5, days=7)`.
- **ML not enabled:** Set `ARGUS_ENABLE_ML=true` in `.env` and restart.
- **Wrong user ID:** Check the `user_id` field — normalisation lowercases and strips domain prefixes, so `DOMAIN\Alice` becomes `alice`.
- **Reviewing the wrong user's profile:** Call `GET /v1/users/{id}/profile` to inspect the baseline directly.

### Problem 4: ModuleNotFoundError on Import

**Symptom:** `ModuleNotFoundError: No module named 'argus'` or `No module named 'fastapi'`.

**Fix:**

```bash
cd path/to/argus     # must be in the project root
pip install -e ".[api,dashboard,ml]"
```

If you have multiple Python versions, make sure you're using the same Python that runs the server.

### Problem 5: argus.db Permission Error

**Symptom:** `PermissionError: [Errno 13] Permission denied: 'argus.db'`

**Fix:**

Check that the current user has write access to the project directory. Alternatively, point the database to a writable location:

```
# In .env
ARGUS_DB_PATH=C:\Users\YourName\Documents\argus.db
```

### Problem 6: React Website Shows Blank Page

**Symptom:** http://localhost:3001 loads but shows nothing, or shows a white screen.

**Checklist:**

1. Did you run `npm install` in the `website/` directory?
2. Check Node.js version: `node --version` — must be 18 or higher.
3. Open browser dev tools (F12) → Console tab — any red errors?
4. Check that the Argus API is running — the website fetches from it on load.
5. If the API is on a different port, create `website/.env.local` with `VITE_ARGUS_API_URL=http://localhost:YOUR_PORT`.

### Problem 7: Docker Containers Won't Start

**Symptom:** `Cannot connect to the Docker daemon` or containers exit immediately.

**Fix:**

1. Make sure Docker Desktop is open and fully started (check the taskbar icon).
2. Verify Docker is working: `docker --version` and `docker ps`.
3. If containers are in a bad state, reset completely:

```bash
docker-compose down -v
docker-compose up --build
```

The `--build` flag forces images to be rebuilt, which resolves most container-state issues.

---

## 16. Quick Reference Card

Everything you need in one place.

```
─────────────────────────────────────────
  ARGUS AI — QUICK REFERENCE
─────────────────────────────────────────

INSTALL
  pip install -e ".[api,dashboard,ml]"

─────────────────────────────────────────
START — WINDOWS (one click)
  Double-click start.bat          ← API + Dashboard
  Double-click start-all.bat      ← API + Dashboard + Website

─────────────────────────────────────────
START — MANUAL (two terminals)
  Terminal 1 (API):
    python -m uvicorn argus.api.server:create_app \
      --factory --host 0.0.0.0 --port 8000

  Terminal 2 (Dashboard):
    python -m streamlit run argus\dashboard\app.py

─────────────────────────────────────────
START — DOCKER
  docker-compose up               ← production
  docker-compose -f docker-compose.dev.yml up  ← dev

─────────────────────────────────────────
WEBSITE (React)
  cd website && npm run dev       ← http://localhost:3001

─────────────────────────────────────────
TEST
  pytest tests/ -v
  pytest tests/ --cov=argus --cov-report=html

─────────────────────────────────────────
SCORE AN EVENT
  curl -X POST http://localhost:8000/v1/events/score \
    -H "Content-Type: application/json" \
    -d '{
      "user_id":"john",
      "timestamp":"2026-06-23T02:15:00",
      "ip":"185.45.67.10",
      "device_id":"unknown",
      "download_mb":5000,
      "files_accessed":600,
      "action":"login"
    }'

─────────────────────────────────────────
CHECK ALERTS
  curl http://localhost:8000/v1/alerts

CHECK HEALTH
  curl http://localhost:8000/health

─────────────────────────────────────────
KEY URLS
  API          →  http://localhost:8000
  API Docs     →  http://localhost:8000/docs
  Dashboard    →  http://localhost:8501
  Website      →  http://localhost:3001

─────────────────────────────────────────
RISK BANDS
  0–30    LOW       Normal — log only
  31–60   MEDIUM    Review within 24h
  61–85   HIGH      Investigate today
  86–100  CRITICAL  Act immediately

─────────────────────────────────────────
TOP SCORING RULES
  Night access (00:00–05:59)   +35 pts
  Large download (>1–5 GB)     +30–50 pts
  Unknown IP                   +20 pts
  Unknown device               +20 pts
  Statistical deviation        +7–30 pts
  Correlation bonus            +20–40 pts
  Threat intel (AbuseIPDB)     +15–40 pts
─────────────────────────────────────────
```

---

*Argus AI — version 0.1.0 — MIT License*
