# Argus Web Test App — Testing Guide

The `web-test` app is a React/Vite frontend that connects to the Argus API and lets you interactively test every major feature of the backend without writing a single `curl` command.

---

## 1. Prerequisites

| Requirement | Version |
|---|---|
| Node.js | 18 or newer |
| npm | 9 or newer |
| Argus API | running on `localhost:8000` |

---

## 2. Start the Argus API

From the repo root:

```bash
# Install Python deps (first time only)
pip install -e .

# Start the API server
argus-serve --port 8000
```

Confirm it is up:

```bash
curl http://localhost:8000/health
# → {"status": "ok", ...}
```

---

## 3. Start the Web Test App

```bash
cd web-test

# Install JS deps (first time only)
npm install

# Start dev server
npm run dev
```

Open **http://localhost:3000** in your browser.

> The dev server proxies `/api/*` to `http://localhost:8000` automatically via `vite.config.js`, so no CORS issues.

---

## 4. Environment Variable (optional)

If your API runs on a different host or port, create a `.env` file:

```bash
# web-test/.env
VITE_ARGUS_API_URL=http://localhost:8000
```

Copy `.env.example` as a starting point:

```bash
cp .env.example .env
```

---

## 5. What to Test — Section by Section

### 5.1 API Status Banner
- Look at the top of the **Live Demo** section.
- **Green / no banner** = API is reachable.
- **Amber warning** = API is offline; the app switches to demo/fake data automatically — all other sections still work for UI review.

---

### 5.2 Live Demo — Score a User Event

This hits `POST /v1/events/score` and shows the full scoring breakdown.

**Quick tests using the preset buttons:**

| Preset | What it sends | Expected result |
|---|---|---|
| Night Threat | `john`, 2 AM, 5 000 MB download, unknown device | HIGH or CRITICAL score |
| Normal User | `alice`, 9:30 AM, 45 MB, known laptop | LOW score |
| Data Exfil | `admin`, 3 AM, 9 800 MB, unknown server | CRITICAL score |

**Manual field testing:**

1. Set **User ID** to any string (e.g. `alice`).
2. Set **IP Address** to a known suspicious IP like `185.45.67.10`.
3. Drag the **Download (MB)** slider to `9 000`.
4. Set **Files Accessed** to `900`.
5. Set **Action** to `download`.
6. Set **Timestamp** to `02:00` (2 AM).
7. Click **Score This Event →**.

**Reading the result panel:**
- The gauge shows the 0–100 risk score.
- The **Contributing Factors** bars show which rules fired and how many points each added.
- Click **Raw Details** to see the raw `rule_contributions` and `stat_contributions` JSON from the API.

---

### 5.3 Alert Feed

This polls `GET /v1/alerts?limit=20&min_risk_level=MEDIUM` every 5 seconds.

- **Live Mode** (green badge): real alerts from the API appear as you score events in the Live Demo.
- **Demo Mode** (amber badge): synthetic fake alerts are generated locally every 3 seconds so the UI is never empty.

**To generate a real alert that appears in the feed:**
1. Score any event with the **Night Threat** or **Data Exfil** preset.
2. Within 5 seconds the alert card should appear at the top of the feed.
3. Click any alert card to expand the full list of reasons.

---

### 5.4 Threat Map

This polls `GET /v1/alerts?limit=50&min_risk_level=LOW` every 15 seconds and maps alert IPs to world coordinates.

- When the API is online, real alert IPs are plotted.
- When offline, 6 demo points are shown (London HIGH, Tokyo CRITICAL, etc.).
- Hover over any dot to see the city, user ID, and risk score tooltip.

---

### 5.5 User Profile Lookup

The API client includes `GET /v1/users/{userId}/profile`. To test it directly:

```bash
# After scoring a few events for "john"
curl http://localhost:8000/v1/users/john/profile
```

---

## 6. API Endpoints Exercised

| UI Section | Method | Endpoint |
|---|---|---|
| API status check | GET | `/health` |
| Live Demo scoring | POST | `/v1/events/score` |
| Alert Feed | GET | `/v1/alerts` |
| Alert stats | GET | `/v1/alerts/stats` |
| Threat Map | GET | `/v1/alerts` (limit 50) |
| Metrics panel | GET | `/metrics` |
| User profile | GET | `/v1/users/{id}/profile` |

---

## 7. Build for Static Hosting (optional)

```bash
cd web-test
npm run build
# Output goes to web-test/dist/
```

Serve the built output:

```bash
npm run preview
# → http://localhost:4173
```

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Amber "API offline" banner | Run `argus-serve --port 8000` and refresh |
| Blank score result | Check browser console for network errors; confirm API returns 200 on `/health` |
| Alert feed empty in Live Mode | Score an event first; alerts only appear after a scored event exceeds MEDIUM |
| `npm install` fails | Ensure Node 18+: `node --version` |
| Port 3000 already in use | `npm run dev -- --port 3001` |
