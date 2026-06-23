"""Authentication log collector for Argus.

Reads login/authentication events from:

* **Linux syslog** (``/var/log/auth.log``) — SSH accepted/failed lines.
* **CSV export** — flexible column order, detected from the header row.
* **JSON Lines** (``.jsonl``) — one JSON object per line.

Format is auto-detected on the first non-empty line. Incremental reads via
``_last_position`` ensure repeated :meth:`AuthCollector.collect` calls never
re-process already-seen lines.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re

from argus.collectors.base import BaseCollector
from argus.collectors.normalize import UNKNOWN_DEVICE, build_event
from argus.schema import Event

logger = logging.getLogger(__name__)


class AuthCollector(BaseCollector):
    """Collect user authentication events from login log files.

    Supports Linux ``auth.log``, CSV exports, and JSON Lines format.
    Format is auto-detected on the first line read.

    Usage::

        collector = AuthCollector("/var/log/auth.log")
        events = collector.collect()
        for event in events:
            result = engine.score(event)
    """

    # SSH accepted: "Jun 16 02:15:00 host sshd[123]: Accepted password for john from 1.2.3.4"
    SYSLOG_LOGIN_PATTERN = re.compile(
        r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Accepted.*for\s+(\S+)\s+from\s+([\d.]+)"
    )
    # SSH failed: "Jun 16 02:15:00 host sshd[123]: Failed password for john from 1.2.3.4"
    SYSLOG_FAILED_PATTERN = re.compile(
        r"(\w+\s+\d+\s+\d+:\d+:\d+).*sshd.*Failed.*for\s+(\S+)\s+from\s+([\d.]+)"
    )

    def __init__(self, source: str, encoding: str = "utf-8") -> None:
        """Initialise the auth collector.

        Args:
            source: Path to the log file to read.
            encoding: File encoding. Defaults to ``"utf-8"``.
        """
        super().__init__(source)
        self.encoding = encoding
        self._last_position: int = 0
        self._format: str | None = None

    # ── Format detection ──────────────────────────────────────────────────────

    def detect_format(self, first_line: str) -> str:
        """Detect the log format from the first non-empty line.

        Args:
            first_line: The first line of the file.

        Returns:
            One of ``"syslog"``, ``"csv"``, or ``"jsonl"``.
        """
        stripped = first_line.strip()
        if stripped.startswith("{"):
            return "jsonl"
        # Heuristic: CSV headers contain commas and typically a "user" column.
        if "," in stripped and not re.match(r"^\w{3}\s+\d", stripped):
            return "csv"
        return "syslog"

    # ── Incremental file read ─────────────────────────────────────────────────

    def collect(self) -> list[Event]:
        """Read new lines from the source file since the last call.

        Uses ``_last_position`` (byte offset) to skip already-processed lines.
        Returns an empty list if the file does not exist.

        Returns:
            List of normalised :class:`~argus.schema.Event` objects.
        """
        if not os.path.isfile(self.source):
            logger.warning("AuthCollector: file not found: %s", self.source)
            return []

        events: list[Event] = []
        try:
            with open(self.source, "r", encoding=self.encoding, errors="replace") as fh:
                fh.seek(self._last_position)
                lines = fh.readlines()
                self._last_position = fh.tell()
        except OSError as exc:
            logger.warning("AuthCollector: cannot read %s: %s", self.source, exc)
            return []

        # Auto-detect format on first content line ever seen.
        if self._format is None:
            for line in lines:
                if line.strip():
                    self._format = self.detect_format(line)
                    break

        for line in lines:
            event = self.parse_line(line)
            if event is not None:
                events.append(event)

        return events

    # ── Line parsers ──────────────────────────────────────────────────────────

    def parse_line(self, raw: str) -> Event | None:
        """Dispatch a raw log line to the appropriate format parser.

        Args:
            raw: One raw line of text from the log file.

        Returns:
            A normalised :class:`~argus.schema.Event`, or ``None`` if the line
            should be skipped.
        """
        try:
            line = raw.strip()
            if not line:
                return None
            fmt = self._format or self.detect_format(line)
            if fmt == "jsonl":
                return self.parse_jsonl_line(line)
            if fmt == "csv":
                return self.parse_csv_line(line)
            return self.parse_syslog_line(line)
        except Exception as exc:
            logger.debug("AuthCollector.parse_line error: %s | line=%r", exc, raw[:80])
            return None

    def parse_syslog_line(self, line: str) -> Event | None:
        """Parse a Linux ``auth.log`` / syslog-format line.

        Only ``Accepted`` (successful) login lines are scored; ``Failed``
        lines are skipped (they carry no session context for profiling).

        Args:
            line: A single syslog line.

        Returns:
            An :class:`~argus.schema.Event` for accepted logins, else ``None``.
        """
        m = self.SYSLOG_LOGIN_PATTERN.search(line)
        if m:
            ts_str, user, ip = m.group(1), m.group(2), m.group(3)
            return build_event(
                user_id=user,
                timestamp=ts_str,
                ip=ip,
                device_id=UNKNOWN_DEVICE,
                action="login",
            )
        # Failed logins — return None (do not score here; no baseline data).
        if self.SYSLOG_FAILED_PATTERN.search(line):
            return None
        return None

    def parse_csv_line(self, line: str) -> Event | None:
        """Parse a CSV-format log line.

        Detects column positions from the header row on first call. Expected
        columns (order flexible): ``user_id``, ``timestamp``, ``ip``,
        ``device_id``, ``action``. Unknown column names are ignored.

        Args:
            line: A single CSV line.

        Returns:
            An :class:`~argus.schema.Event`, or ``None`` for the header row or
            unparseable lines.
        """
        try:
            reader = csv.reader(io.StringIO(line))
            row = next(reader)
        except Exception:
            return None

        # Skip header
        lower = [c.lower().strip() for c in row]
        if any(h in lower for h in ("user_id", "user", "username", "timestamp", "time")):
            if not hasattr(self, "_csv_header"):
                self._csv_header = lower  # type: ignore[attr-defined]
            return None

        header = getattr(self, "_csv_header", None)
        if header is None or len(row) < 2:
            return None

        def _get(col_names: list[str], default: str = "") -> str:
            for name in col_names:
                if name in header:
                    idx = header.index(name)
                    if idx < len(row):
                        return row[idx].strip()
            return default

        user     = _get(["user_id", "user", "username"])
        ts       = _get(["timestamp", "time", "date"])
        ip       = _get(["ip", "src_ip", "source_ip", "remote_ip"])
        device   = _get(["device_id", "device", "hostname", "host"])
        action   = _get(["action", "event", "type"], default="login")
        dl_raw   = _get(["download_mb", "bytes", "download"])
        files_r  = _get(["files_accessed", "files"])

        if not user or not ts:
            return None

        return build_event(
            user_id=user,
            timestamp=ts,
            ip=ip or None,
            device_id=device or None,
            download_mb=dl_raw or None,
            files_accessed=files_r or None,
            action=action,
        )

    def parse_jsonl_line(self, line: str) -> Event | None:
        """Parse a JSON Lines format log line.

        Expected keys: ``user_id``, ``timestamp``, ``ip``, ``device_id``,
        ``action``. All other keys are silently ignored.

        Args:
            line: A single JSON object as a string.

        Returns:
            An :class:`~argus.schema.Event`, or ``None`` on parse error.
        """
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None

        user = obj.get("user_id") or obj.get("user") or obj.get("username")
        ts   = obj.get("timestamp") or obj.get("time") or obj.get("date")
        if not user or not ts:
            return None

        return build_event(
            user_id=str(user),
            timestamp=str(ts),
            ip=obj.get("ip") or obj.get("src_ip"),
            device_id=obj.get("device_id") or obj.get("device") or obj.get("hostname"),
            download_mb=obj.get("download_mb") or obj.get("bytes"),
            files_accessed=obj.get("files_accessed") or obj.get("files"),
            action=str(obj.get("action", "login")),
            location=obj.get("location"),
        )
