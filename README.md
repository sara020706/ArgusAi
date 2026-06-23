# Argus

Argus is a zero-dependency, pip-installable Python package for detecting insider
threats and anomalous user behavior. Any application can import Argus, pass it a
single user activity event together with a profile of that user's normal
behavior, and receive back a **0-100 risk score**, a categorical **risk level**
(`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`), and a **human-readable explanation** of
exactly which factors drove the score.

## Installation

```bash
# From PyPI (once published)
pip install argus

# For local development (editable install from the project root)
pip install -e .

# Optional extras
pip install -e ".[ml]"    # ML anomaly detection (scikit-learn)
pip install -e ".[api]"   # REST API server (FastAPI + uvicorn)
pip install -e ".[dev]"   # test + ML tooling (pytest, coverage, scikit-learn)
```

Argus targets Python 3.10+. The **core has no runtime dependencies** — only the
standard library. scikit-learn (ML) and FastAPI/uvicorn (API) are *optional*
extras; the package imports and scores fine without them.

## Usage

```python
from datetime import datetime
from argus import score, Event
from argus.explainer import build_explanation

# 1. Create an event describing a single user action.
event = Event(
    user_id="john",
    timestamp=datetime(2026, 6, 16, 2, 15),
    ip="185.45.67.10",
    device_id="unknown-device-44",
    download_mb=5000,
    files_accessed=600,
    action="download",
)

# 2. Describe the user's normal behavior.
user_profile = {
    "avg_download_mb": 47.0,
    "std_download_mb": 12.0,
    "avg_files_accessed": 20.0,
    "std_files_accessed": 5.0,
    "known_ips": ["192.168.1.5"],
    "known_devices": ["work-laptop-01"],
}

# 3. Score the event.
result = score(event, user_profile)

# 4. Print a full human-readable explanation.
print(build_explanation(result))
```

You can also get a clean, JSON-serializable summary:

```python
import json
from argus.explainer import summarize_result

print(json.dumps(summarize_result(result), indent=2))
```

## Stateful engine (managed profiles)

Instead of passing a profile dict yourself, let `ArgusEngine` maintain adaptive
per-user baselines through a storage backend. It loads (or creates) the user's
profile, scores the event, updates the baseline, and persists everything.

```python
from argus import ArgusEngine, Event
from argus.storage import MemoryStore  # or SQLiteStore("argus.db")

engine = ArgusEngine(store=MemoryStore())
result = engine.score(event)

print(result.risk_score, result.risk_level)
print(engine.get_recent_alerts(min_risk_level="HIGH"))
```

`SQLiteStore` is the zero-setup default; implement `ArgusStore` to plug Argus
into your own database.

### Optional layers

```python
from argus import ArgusEngine, IsolationForestDetector, ThreatIntelClient
from argus.storage import SQLiteStore

engine = ArgusEngine(
    store=SQLiteStore("argus.db"),
    detector=IsolationForestDetector(),        # ML anomaly layer (max +20 pts)
    threat_intel=ThreatIntelClient(api_key=None),  # IP reputation (AbuseIPDB)
)
engine.train()  # trains the ML detector on synthetic data, saves argus_model.pkl
```

Multi-event **correlation** (escalating downloads, slow exfiltration,
reconnaissance, repeated night logins, account-takeover indicators) is applied
automatically by the engine over each user's recent activity window.

## REST API

```bash
pip install -e ".[api]"
argus-serve            # serves on 0.0.0.0:8000; OpenAPI docs at /docs
```

```python
from argus.api import create_app
app = create_app(db_path="argus.db", enable_ml=False)
```

Key endpoints: `POST /v1/events/score`, `POST /v1/events/batch` (≤100),
`GET /v1/alerts`, `GET /v1/alerts/stats`, `GET /v1/users/{id}/profile`,
`GET /v1/users/{id}/risk_summary`, `GET /health`, `GET /metrics`. Set the
`API_KEY` environment variable to require an `X-API-Key` header on all routes
except health and docs.

## Module overview

| Module                       | Responsibility                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `schema.py`                  | Defines the `Event` input and `ScoreResult` output dataclasses.                |
| `features.py`                | Pure functions that turn an `Event` + profile into a flat feature vector.      |
| `rules.py`                   | Heuristic rules (night access, new IP/device, large download, etc.).           |
| `statistics.py`              | Converts per-user statistical deviations (z-scores) into risk points.          |
| `scorer.py`                  | Combines rules and stats into a capped score and a `ScoreResult`.              |
| `explainer.py`               | Renders a `ScoreResult` as a readable report or JSON-serializable summary.     |
| `profile.py`                 | `UserProfile` — adaptive per-user baselines via Welford's online algorithm.    |
| `storage/`                   | `ArgusStore` interface + `SQLiteStore` and `MemoryStore` backends.             |
| `detectors.py`               | Optional `IsolationForestDetector` ML anomaly layer (scikit-learn).            |
| `synthetic/`                 | Synthetic normal/anomalous activity generator for training & testing.          |
| `correlator.py`              | Multi-event attack-pattern correlation over a per-user time window.            |
| `integrations/threat_intel.py` | `ThreatIntelClient` — AbuseIPDB IP-reputation lookups (stdlib `urllib`).     |
| `api/`                       | FastAPI REST server (`create_app`, `argus-serve`) exposing all capabilities.   |
| `__init__.py`                | Public API: `Event`, `score`, `ArgusEngine`, and the components above.         |
