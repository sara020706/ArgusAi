"""File-system access collector for Argus.

Reads file access events and groups them into per-user, per-time-window
:class:`~argus.schema.Event` objects (one event per user per window, with
``files_accessed`` = distinct file count). This prevents individual file
touches from flooding the scoring engine.

Supports:

* **Linux auditd** log format (``/var/log/audit/audit.log``).
* **CSV access log** — columns: ``timestamp,user_id,file_path,action``.
* **Live monitoring via watchdog** — optional; guarded import.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Callable

from argus.collectors.base import BaseCollector
from argus.collectors.normalize import UNKNOWN_IP, build_event, normalize_timestamp
from argus.schema import Event

logger = logging.getLogger(__name__)


class FileCollector(BaseCollector):
    """Collect file-system access events and group them by user and time window.

    Reads from a Linux auditd log or a CSV access log. Groups raw per-file
    events into a single :class:`~argus.schema.Event` per ``(user, window)``
    pair so the scoring engine receives a meaningful signal rather than one
    event per file touch.

    Watchdog (live monitoring) is optional. Install with
    ``pip install argus[files]``.

    Usage::

        collector = FileCollector(
            source="/var/log/audit/audit.log",
            watch_path="/home/sensitive_data",
        )
        events = collector.collect()
    """

    SENSITIVE_EXTENSIONS = {
        ".pdf", ".docx", ".xlsx", ".csv", ".sql",
        ".pem", ".key", ".env", ".config", ".bak",
    }

    # auditd SYSCALL line: type=SYSCALL … uid=1000 … comm="cat" … name="/etc/passwd"
    AUDIT_PATTERN = re.compile(
        r'type=SYSCALL.*?uid=(\d+).*?comm="([^"]+)".*?name="([^"]+)"'
    )

    def __init__(
        self,
        source: str,
        watch_path: str | None = None,
        window_minutes: int = 5,
        uid_to_user: dict[str, str] | None = None,
    ) -> None:
        """Initialise the file collector.

        Args:
            source: Path to an audit log file, a CSV access log, or
                ``"live"`` to use watchdog for real-time monitoring.
            watch_path: Directory to monitor in live mode.
            window_minutes: Time window for grouping per-user file events.
            uid_to_user: Maps Linux UID strings to usernames. Optional.
        """
        super().__init__(source)
        self.watch_path = watch_path
        self.window_minutes = window_minutes
        self.uid_to_user = uid_to_user or {}
        self._last_position: int = 0
        self._event_buffer: dict[str, list] = {}
        self._csv_header: list[str] | None = None

    # ── Collect ───────────────────────────────────────────────────────────────

    def collect(self) -> list[Event]:
        """Read file access records since the last call and group them.

        For each ``(user_id, time-window)`` pair, produces a single
        :class:`~argus.schema.Event` with ``files_accessed`` = distinct file
        count and ``download_mb`` estimated from sensitive file count.

        Returns:
            List of grouped :class:`~argus.schema.Event` objects. Empty list
            if the source file is not found.
        """
        if self.source == "live":
            logger.warning("FileCollector: live mode requires start_live_monitoring().")
            return []

        if not os.path.isfile(self.source):
            logger.warning("FileCollector: file not found: %s", self.source)
            return []

        raw_records: list[dict] = []
        try:
            with open(self.source, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self._last_position)
                lines = fh.readlines()
                self._last_position = fh.tell()
        except OSError as exc:
            logger.warning("FileCollector: cannot read %s: %s", self.source, exc)
            return []

        for line in lines:
            record = self.parse_line(line)
            if record is not None:
                raw_records.append(record)  # type: ignore[arg-type]

        return self.group_into_events(raw_records)

    # ── Line parsers ──────────────────────────────────────────────────────────

    def parse_line(self, raw: str) -> Event | None:
        """Parse one log line; return a raw dict (not an Event) or None.

        Dispatches to :meth:`parse_audit_line` or :meth:`parse_csv_line`
        based on line content. Returns ``None`` for unrecognised lines.

        .. note::
            This method returns a ``dict`` (raw record) rather than an
            :class:`~argus.schema.Event` because grouping happens later in
            :meth:`group_into_events`. The :class:`~argus.collectors.base.BaseCollector`
            abstract signature allows ``None`` returns.

        Args:
            raw: One raw log line.

        Returns:
            A raw record dict, or ``None``.
        """
        try:
            line = raw.strip()
            if not line:
                return None
            if line.startswith("type="):
                return self.parse_audit_line(line)  # type: ignore[return-value]
            return self.parse_csv_line(line)  # type: ignore[return-value]
        except Exception as exc:
            logger.debug("FileCollector.parse_line error: %s | line=%r", exc, raw[:80])
            return None

    def parse_audit_line(self, line: str) -> dict | None:
        """Parse a Linux auditd ``SYSCALL`` line.

        Args:
            line: A single auditd log line starting with ``type=SYSCALL``.

        Returns:
            A dict with ``uid``, ``command``, ``filename``, and ``timestamp``
            keys, or ``None`` if not a file-access SYSCALL.
        """
        m = self.AUDIT_PATTERN.search(line)
        if not m:
            return None
        uid, command, filename = m.group(1), m.group(2), m.group(3)

        # Extract timestamp from audit record: "audit(1750039800.123:456)"
        ts_match = re.search(r"audit\((\d+)\.\d+:\d+\)", line)
        ts_str = ts_match.group(1) if ts_match else ""

        return {
            "user_id": self.uid_to_user.get(uid, f"uid_{uid}"),
            "filename": filename,
            "command": command,
            "timestamp": ts_str or datetime.now().isoformat(),
        }

    def parse_csv_line(self, line: str) -> dict | None:
        """Parse a CSV-format file access log line.

        Expected columns: ``timestamp``, ``user_id``, ``file_path``,
        ``action`` (order detected from the header row on first call).

        Args:
            line: A single CSV line.

        Returns:
            A raw record dict, or ``None`` for the header or empty lines.
        """
        try:
            reader = csv.reader(io.StringIO(line))
            cols = next(reader)
        except Exception:
            return None

        lower = [c.lower().strip() for c in cols]

        # Header row
        if any(h in lower for h in ("timestamp", "time", "user_id", "user", "file_path")):
            self._csv_header = lower
            return None

        header = self._csv_header
        if header is None or len(cols) < 2:
            return None

        def _get(names: list[str], default: str = "") -> str:
            for name in names:
                if name in header:
                    idx = header.index(name)
                    if idx < len(cols):
                        return cols[idx].strip()
            return default

        ts   = _get(["timestamp", "time", "date"])
        user = _get(["user_id", "user", "username"])
        fp   = _get(["file_path", "filename", "file", "path"])
        action = _get(["action", "event", "type"], default="open")

        if not user or not ts:
            return None

        return {
            "user_id": user,
            "filename": fp,
            "command": action,
            "timestamp": ts,
        }

    # ── Grouping ──────────────────────────────────────────────────────────────

    def is_sensitive_file(self, file_path: str) -> bool:
        """Return ``True`` if the file has a sensitive extension.

        Args:
            file_path: The full or partial file path to check.

        Returns:
            ``True`` if the file extension is in :attr:`SENSITIVE_EXTENSIONS`.
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.SENSITIVE_EXTENSIONS

    def group_into_events(self, raw_records: list[dict]) -> list[Event]:
        """Group raw file-access records into per-user, per-window events.

        For each ``(user_id, time-window)`` pair:

        * ``files_accessed`` = number of distinct filenames accessed.
        * ``download_mb`` = ``sensitive_file_count * 0.5 MB`` (proxy for data
          exfil risk when we cannot measure actual bytes transferred).

        Args:
            raw_records: List of raw dicts from :meth:`parse_line`.

        Returns:
            One :class:`~argus.schema.Event` per ``(user, window)`` pair.
        """
        # Bucket: key → {"files": set, "sensitive": int, "first_ts": datetime}
        buckets: dict[tuple, dict] = defaultdict(lambda: {
            "files": set(),
            "sensitive": 0,
            "first_ts": None,
        })

        for r in raw_records:
            ts = normalize_timestamp(r.get("timestamp", ""))
            floored = ts.replace(
                minute=(ts.minute // self.window_minutes) * self.window_minutes,
                second=0,
                microsecond=0,
            )
            key = (r.get("user_id", "unknown"), floored)
            b = buckets[key]
            fname = r.get("filename", "")
            b["files"].add(fname)
            if self.is_sensitive_file(fname):
                b["sensitive"] += 1
            if b["first_ts"] is None:
                b["first_ts"] = ts

        events: list[Event] = []
        for (user_id, floored), b in sorted(buckets.items(), key=lambda x: x[0][1]):
            events.append(build_event(
                user_id=user_id,
                timestamp=b["first_ts"] or floored,
                ip=None,
                download_mb=b["sensitive"] * 0.5,
                files_accessed=len(b["files"]),
                action="file_access",
            ))
        return events

    # ── Live monitoring ───────────────────────────────────────────────────────

    def start_live_monitoring(self, callback: Callable[[Event], None]) -> None:
        """Start real-time file-system monitoring using watchdog.

        Calls ``callback`` with a grouped :class:`~argus.schema.Event` every
        ``window_minutes`` minutes of accumulated activity.

        Args:
            callback: Called with each produced event.

        Raises:
            ImportError: If ``watchdog`` is not installed, with a message
                pointing to ``pip install argus[files]``.
        """
        try:
            from watchdog.events import FileSystemEventHandler  # type: ignore
            from watchdog.observers import Observer              # type: ignore
        except ImportError as exc:
            raise ImportError(
                "watchdog is required for live file monitoring. "
                "Install with: pip install argus[files]"
            ) from exc

        watch_path = self.watch_path or os.getcwd()
        raw_buffer: list[dict] = []

        class _Handler(FileSystemEventHandler):
            def on_any_event(self_, event):  # noqa: N805
                if event.is_directory:
                    return
                raw_buffer.append({
                    "user_id": "live_user",
                    "filename": event.src_path,
                    "command": event.event_type,
                    "timestamp": datetime.now().isoformat(),
                })

        observer = Observer()
        observer.schedule(_Handler(), path=watch_path, recursive=True)
        observer.start()
        logger.info("FileCollector: live monitoring started on %s", watch_path)

        import time
        try:
            while True:
                time.sleep(self.window_minutes * 60)
                if raw_buffer:
                    events = self.group_into_events(list(raw_buffer))
                    raw_buffer.clear()
                    for e in events:
                        callback(e)
        finally:
            observer.stop()
            observer.join()
