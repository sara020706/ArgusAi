"""Network traffic collector for Argus.

Reads network flow records and converts them into user-attributed
download/upload :class:`~argus.schema.Event` objects. Supports:

* **NetFlow CSV export** — standard columns including ``bytes``.
* **Simple traffic log** — ``timestamp,src_ip,dst_ip,bytes[,protocol]``.
* **Live capture via PyShark** — optional; guarded import inside the method.

The host application provides an ``ip_to_user`` mapping so the collector can
attribute traffic to a named user rather than a raw IP address.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import re
from collections import defaultdict

from argus.collectors.base import BaseCollector
from argus.collectors.normalize import build_event, normalize_ip
from argus.schema import Event

logger = logging.getLogger(__name__)

_IFACE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.\-]{0,14}$")


class NetworkCollector(BaseCollector):
    """Collect network traffic events and attribute them to users.

    Maps IP addresses to user IDs via ``ip_to_user``. Without a mapping the IP
    address itself is used as the ``user_id``. Traffic below ``min_mb`` is
    filtered out to reduce noise.

    PyShark (live capture) is optional — if not installed, only file-based
    sources work. Install it with ``pip install argus[network]``.

    Usage::

        collector = NetworkCollector(
            source="traffic.csv",
            ip_to_user={"192.168.1.5": "john"}
        )
        events = collector.collect()
    """

    def __init__(
        self,
        source: str,
        ip_to_user: dict[str, str] | None = None,
        direction: str = "download",
        min_mb: float = 0.1,
    ) -> None:
        """Initialise the network collector.

        Args:
            source: Path to a traffic CSV file, or a network interface name
                (e.g. ``"eth0"``) for live PyShark capture.
            ip_to_user: Dict mapping ``"ip"`` → ``"user_id"``. If ``None``,
                the source IP is used as the user identifier.
            direction: One of ``"download"``, ``"upload"``, or ``"both"``.
                Controls which side of the flow is used as the user.
            min_mb: Minimum transfer size in MB to record. Transfers smaller
                than this are silently discarded.
        """
        super().__init__(source)
        self.ip_to_user = ip_to_user or {}
        self.direction = direction
        self.min_mb = min_mb
        self._last_position: int = 0
        self._header: list[str] | None = None

    # ── Collect ───────────────────────────────────────────────────────────────

    def collect(self) -> list[Event]:
        """Read traffic records from the source file or live interface.

        For file sources, uses ``_last_position`` for incremental reads.
        For interface names (e.g. ``"eth0"``), attempts live PyShark capture;
        falls back to an empty list with a warning if PyShark is unavailable.

        Returns:
            List of normalised :class:`~argus.schema.Event` objects.
        """
        if _IFACE_RE.match(self.source) and not os.path.isfile(self.source):
            return self._collect_live()

        if not os.path.isfile(self.source):
            logger.warning("NetworkCollector: file not found: %s", self.source)
            return []

        events: list[Event] = []
        try:
            with open(self.source, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self._last_position)
                lines = fh.readlines()
                self._last_position = fh.tell()
        except OSError as exc:
            logger.warning("NetworkCollector: cannot read %s: %s", self.source, exc)
            return []

        for line in lines:
            event = self.parse_line(line)
            if event is not None:
                events.append(event)

        return self.aggregate_by_user(events)

    def _collect_live(self) -> list[Event]:
        """Attempt a live packet capture via PyShark.

        Returns:
            Empty list with a warning if PyShark is not installed.
        """
        try:
            import pyshark  # type: ignore  # noqa: F401
        except ImportError:
            logger.warning(
                "NetworkCollector: PyShark not installed. "
                "Install with: pip install argus[network]"
            )
            return []
        logger.info("NetworkCollector: live capture on %s is not yet implemented.", self.source)
        return []

    # ── Parsing ───────────────────────────────────────────────────────────────

    def parse_line(self, raw: str) -> Event | None:
        """Parse one traffic record line.

        Auto-detects NetFlow CSV vs simple traffic log format from column
        count. Filters transfers below ``min_mb``.

        Args:
            raw: One raw line of text.

        Returns:
            An :class:`~argus.schema.Event`, or ``None`` if the line should be
            skipped (header, below threshold, or parse error).
        """
        try:
            line = raw.strip()
            if not line:
                return None
            try:
                reader = csv.reader(io.StringIO(line))
                cols = next(reader)
            except Exception:
                return None

            lower = [c.lower().strip() for c in cols]

            # Detect / store header row
            if any(h in lower for h in ("timestamp", "time", "src_ip", "src", "bytes", "octets")):
                self._header = lower
                return None

            header = self._header or []

            def _col(names: list[str], default: str = "") -> str:
                for name in names:
                    if name in header:
                        idx = header.index(name)
                        if idx < len(cols):
                            return cols[idx].strip()
                return default

            # NetFlow CSV (has named columns)
            if header:
                ts_raw   = _col(["timestamp", "time", "start", "first_switched"])
                src_ip   = _col(["src_ip", "src", "srcaddr", "ipv4_src_addr"])
                dst_ip   = _col(["dst_ip", "dst", "dstaddr", "ipv4_dst_addr"])
                bytes_r  = _col(["bytes", "octets", "in_bytes", "out_bytes"])
            else:
                # Simple format: timestamp,src_ip,dst_ip,bytes[,proto]
                if len(cols) < 4:
                    return None
                ts_raw, src_ip, dst_ip, bytes_r = cols[0], cols[1], cols[2], cols[3]

            bytes_val = float(re.sub(r"[^\d.]", "", bytes_r) or "0")
            mb = bytes_val / (1024 * 1024)
            if mb < self.min_mb:
                return None

            user_ip = normalize_ip(src_ip if self.direction in ("download", "both") else dst_ip)
            user_id = self.resolve_user(user_ip)

            return build_event(
                user_id=user_id,
                timestamp=ts_raw,
                ip=user_ip,
                download_mb=mb,
                files_accessed=0,
                action="download",
            )
        except Exception as exc:
            logger.debug("NetworkCollector.parse_line error: %s | line=%r", exc, raw[:80])
            return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def resolve_user(self, ip: str) -> str:
        """Resolve an IP address to a user ID via ``ip_to_user``.

        Args:
            ip: The bare IP address string.

        Returns:
            The mapped user ID, or the IP itself if not in the mapping.
        """
        return self.ip_to_user.get(ip, ip)

    def aggregate_by_user(
        self,
        events: list[Event],
        window_minutes: int = 5,
    ) -> list[Event]:
        """Aggregate small per-packet events into per-user time-window events.

        Groups events by ``(user_id, window)`` where *window* is the
        ``timestamp`` floored to ``window_minutes``. Within each group, sums
        ``download_mb`` and takes the maximum ``files_accessed``.

        This prevents a single large file transfer split across many packets
        from flooding the scoring engine with hundreds of micro-events.

        Args:
            events: Raw per-packet events.
            window_minutes: Width of the aggregation window in minutes.

        Returns:
            A smaller list of aggregated :class:`~argus.schema.Event` objects.
        """
        buckets: dict[tuple, dict] = defaultdict(lambda: {
            "download_mb": 0.0,
            "files_accessed": 0,
            "ip": "",
            "device_id": "",
            "action": "download",
            "first_ts": None,
        })

        for e in events:
            floored = e.timestamp.replace(
                minute=(e.timestamp.minute // window_minutes) * window_minutes,
                second=0,
                microsecond=0,
            )
            key = (e.user_id, floored)
            b = buckets[key]
            b["download_mb"] += e.download_mb
            b["files_accessed"] = max(b["files_accessed"], e.files_accessed)
            b["ip"] = b["ip"] or e.ip
            b["device_id"] = b["device_id"] or e.device_id
            if b["first_ts"] is None:
                b["first_ts"] = e.timestamp

        result: list[Event] = []
        for (user_id, floored), b in sorted(buckets.items(), key=lambda x: x[0][1]):
            result.append(build_event(
                user_id=user_id,
                timestamp=b["first_ts"] or floored,
                ip=b["ip"] or None,
                device_id=b["device_id"] or None,
                download_mb=b["download_mb"],
                files_accessed=b["files_accessed"],
                action=b["action"],
            ))
        return result
