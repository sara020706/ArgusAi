"""Simulation helpers for testing Argus collectors without real data sources.

Generates realistic synthetic log files and runs end-to-end simulations
through an :class:`~argus.ArgusEngine`. All functions are pure (no global
state) and use stdlib only (``random``, ``datetime``, ``os``).
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

_ROLES = ["analyst", "developer", "executive", "sysadmin"]
_OFFICE_IPS = ["192.168.1.{}".format(i) for i in range(1, 20)]
_DEVICES = ["laptop-{:02d}".format(i) for i in range(1, 10)]
_ANOMALY_TYPES = ["night_login", "data_exfil", "unknown_ip", "unknown_device", "combined"]
_SENSITIVE_FILES = [
    "/etc/passwd", "/etc/shadow", "/home/user/salary.xlsx",
    "/data/customers.csv", "/secrets/api.key", "/backup/db.sql",
]
_NORMAL_FILES = [
    "/home/user/notes.txt", "/var/log/app.log", "/tmp/work.tmp",
    "/home/user/report.docx", "/data/public.csv",
]

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _rand_hour(mean: float, std: float, low: float = 0.0, high: float = 23.9) -> float:
    """Gaussian-clamped hour draw."""
    return max(low, min(high, random.gauss(mean, std)))


def _dt(base: datetime, hour_float: float) -> datetime:
    h = int(hour_float) % 24
    m = int((hour_float - int(hour_float)) * 60) % 60
    return base.replace(hour=h, minute=m, second=random.randint(0, 59))


def _syslog_ts(dt: datetime) -> str:
    """Format a datetime as syslog timestamp: "Jun 16 02:15:00"."""
    return f"{_MONTHS[dt.month - 1]} {dt.day:2d} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"


def simulate_auth_log(
    output_path: str,
    n_users: int = 5,
    days: int = 7,
    anomaly_rate: float = 0.05,
) -> str:
    """Write a realistic Linux ``auth.log``-format file to disk.

    Generates a mix of successful logins (normal and anomalous) for
    ``n_users`` users over ``days`` days. Anomalous events are injected at
    ``anomaly_rate`` frequency.

    Args:
        output_path: Destination file path.
        n_users: Number of distinct users to simulate.
        days: Number of days of activity to generate.
        anomaly_rate: Fraction of events that are anomalous (0–1).

    Returns:
        ``output_path`` (for chaining).
    """
    start = datetime(2026, 1, 1)
    host = "argus-server"
    lines: list[str] = []

    for u in range(n_users):
        user = f"user{u:03d}"
        ip = random.choice(_OFFICE_IPS)

        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() >= 5 and random.random() < 0.8:
                continue

            is_anomaly = random.random() < anomaly_rate
            atype = random.choice(_ANOMALY_TYPES) if is_anomaly else None

            if atype == "night_login" or atype == "combined":
                hour = _rand_hour(2.0, 0.5, 0.5, 4.5)
            else:
                hour = _rand_hour(9.0, 1.0, 7.0, 18.9)

            event_ip = ip
            if atype in ("unknown_ip", "combined"):
                event_ip = "185.{}.{}.{}".format(
                    random.randint(1, 254), random.randint(1, 254), random.randint(1, 254)
                )

            ts = _dt(day, hour)
            ts_str = _syslog_ts(ts)
            pid = random.randint(1000, 9999)

            lines.append(
                f"{ts_str} {host} sshd[{pid}]: Accepted password for {user} "
                f"from {event_ip} port {random.randint(10000, 65535)} ssh2\n"
            )

            # Occasionally inject a failed attempt before the success
            if random.random() < 0.1:
                fail_ts = _syslog_ts(ts.replace(second=max(0, ts.second - 5)))
                lines.append(
                    f"{fail_ts} {host} sshd[{pid}]: Failed password for {user} "
                    f"from {event_ip} port {random.randint(10000, 65535)} ssh2\n"
                )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    return output_path


def simulate_network_log(
    output_path: str,
    n_users: int = 5,
    days: int = 7,
    anomaly_rate: float = 0.05,
) -> str:
    """Write a CSV network traffic log to disk.

    Columns: ``timestamp,src_ip,dst_ip,bytes,protocol``.

    Args:
        output_path: Destination file path.
        n_users: Number of distinct users (mapped to IPs) to simulate.
        days: Number of days of activity.
        anomaly_rate: Fraction of events that are large-download anomalies.

    Returns:
        ``output_path``.
    """
    start = datetime(2026, 1, 1)
    lines = ["timestamp,src_ip,dst_ip,bytes,protocol\n"]
    user_ips = [random.choice(_OFFICE_IPS) for _ in range(n_users)]
    dst_ips = ["10.0.0.{}".format(i) for i in range(1, 5)]

    for u in range(n_users):
        src = user_ips[u]
        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() >= 5 and random.random() < 0.8:
                continue

            n_flows = random.randint(2, 8)
            for _ in range(n_flows):
                hour = _rand_hour(9.5, 1.5, 7.0, 19.0)
                ts = _dt(day, hour).strftime("%Y-%m-%dT%H:%M:%S")
                is_anomaly = random.random() < anomaly_rate
                bytes_val = (
                    random.randint(2_000_000, 8_000_000) * 1024  # GB-range anomaly
                    if is_anomaly
                    else random.randint(10_000, 500_000)          # normal KB-MB
                )
                proto = random.choice(["TCP", "UDP", "HTTPS"])
                lines.append(
                    f"{ts},{src},{random.choice(dst_ips)},{bytes_val},{proto}\n"
                )

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    return output_path


def simulate_file_log(
    output_path: str,
    n_users: int = 5,
    days: int = 7,
    anomaly_rate: float = 0.05,
) -> str:
    """Write a CSV file-access log to disk.

    Columns: ``timestamp,user_id,file_path,action``.

    Args:
        output_path: Destination file path.
        n_users: Number of distinct users.
        days: Number of days of activity.
        anomaly_rate: Fraction of events that are bulk-access anomalies.

    Returns:
        ``output_path``.
    """
    start = datetime(2026, 1, 1)
    lines = ["timestamp,user_id,file_path,action\n"]
    actions = ["open", "read", "write", "copy"]

    for u in range(n_users):
        user = f"user{u:03d}"
        for d in range(days):
            day = start + timedelta(days=d)
            if day.weekday() >= 5 and random.random() < 0.8:
                continue

            is_anomaly = random.random() < anomaly_rate
            n_files = random.randint(200, 600) if is_anomaly else random.randint(3, 20)
            hour = _rand_hour(1.5 if is_anomaly else 9.5, 0.5, 0.0, 23.9)

            for _ in range(n_files):
                ts = _dt(day, hour + random.uniform(0, 0.5)).strftime("%Y-%m-%dT%H:%M:%S")
                fp = random.choice(_SENSITIVE_FILES if is_anomaly else _NORMAL_FILES)
                action = random.choice(actions)
                lines.append(f"{ts},{user},{fp},{action}\n")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    return output_path


def run_simulation(
    engine,
    n_users: int = 5,
    days: int = 7,
    print_alerts: bool = True,
) -> list[dict]:
    """Run a full end-to-end simulation through an :class:`~argus.ArgusEngine`.

    Generates synthetic events using the Phase 3 generator, scores each
    through ``engine``, and optionally prints ``HIGH``/``CRITICAL`` alerts.

    Args:
        engine: An initialised :class:`~argus.ArgusEngine` instance.
        n_users: Number of synthetic users to generate.
        days: Number of days of activity to simulate.
        print_alerts: If ``True``, prints each HIGH+ alert to stdout.

    Returns:
        A list of dicts — one per scored event — containing ``user_id``,
        ``timestamp``, ``risk_score``, ``risk_level``, and ``reasons``.
    """
    from argus.synthetic.generator import generate_dataset

    events, _labels = generate_dataset(n_users=n_users, days=days, anomaly_rate=0.05)

    results: list[dict] = []
    for event in events:
        result = engine.score(event)
        entry = {
            "user_id":    result.user_id,
            "timestamp":  result.timestamp.isoformat(),
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "reasons":    result.reasons,
        }
        results.append(entry)

        if print_alerts and result.risk_level in ("HIGH", "CRITICAL"):
            print(
                f"[ARGUS] {result.risk_level:8s} | "
                f"user={result.user_id} | "
                f"score={result.risk_score:.0f} | "
                f"ts={result.timestamp.strftime('%Y-%m-%d %H:%M')} | "
                f"{result.reasons[0] if result.reasons else ''}"
            )

    return results
