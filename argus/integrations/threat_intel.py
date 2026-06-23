"""Threat-intelligence integration for Argus.

:class:`ThreatIntelClient` cross-references IP addresses against AbuseIPDB and
converts the result into risk points. It is built to be safe and optional:

* uses only :mod:`urllib` from the standard library (no ``requests``);
* every network call has a 3-second timeout and is wrapped so failures return a
  neutral result rather than raising;
* RFC1918 private IPs are never sent to the external API;
* without an API key, all lookups return a neutral, non-malicious result;
* results are cached (in memory, or via a provided store) so each IP is looked
  up at most once per TTL.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from argus.storage.base import ArgusStore

# Request timeout for all outbound calls, in seconds (per spec).
_REQUEST_TIMEOUT_SECONDS = 3.0


def _neutral_result(ip: str, source: str = "unavailable") -> dict:
    """Build a neutral (non-malicious) reputation result.

    Args:
        ip: The IP the result is for.
        source: Where the result came from (``"unavailable"``, ``"cache"`` or
            ``"api"``).

    Returns:
        A reputation dict with no abuse signal.
    """
    return {
        "ip": ip,
        "is_malicious": False,
        "abuse_score": 0,
        "country": None,
        "isp": None,
        "total_reports": 0,
        "source": source,
    }


class ThreatIntelClient:
    """Looks up IP reputation via AbuseIPDB with caching and graceful fallback."""

    ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"

    def __init__(
        self,
        api_key: str | None = None,
        cache_ttl_hours: int = 24,
        store: ArgusStore | None = None,
    ):
        """Configure the threat-intel client.

        Args:
            api_key: AbuseIPDB API key. If ``None``, lookups are skipped and all
                IPs return a neutral result.
            cache_ttl_hours: How long a cached reputation result remains valid.
            store: Optional storage backend (reserved for shared caching).
                When ``None``, an in-memory dict cache is used.
        """
        self.api_key = api_key
        self.cache_ttl_hours = cache_ttl_hours
        self.store = store
        self._memory_cache: dict[str, dict] = {}

    def _is_private_ip(self, ip: str) -> bool:
        """Return True for RFC1918 private IP ranges (never looked up).

        Covers ``10.0.0.0/8``, ``172.16.0.0/12``, ``192.168.0.0/16`` plus
        loopback (``127.0.0.0/8``). Malformed input is treated as private so it
        is never sent to the external API.

        Args:
            ip: The IP address string to test.

        Returns:
            ``True`` if the IP is private/loopback/unparseable, else ``False``.
        """
        parts = ip.split(".")
        if len(parts) != 4:
            return True
        try:
            octets = [int(p) for p in parts]
        except ValueError:
            return True
        if any(o < 0 or o > 255 for o in octets):
            return True

        a, b = octets[0], octets[1]
        if a == 10:
            return True
        if a == 172 and 16 <= b <= 31:
            return True
        if a == 192 and b == 168:
            return True
        if a == 127:
            return True
        return False

    def _cache_result(self, ip: str, result: dict) -> None:
        """Store a result in the in-memory cache with a fetch timestamp.

        Args:
            ip: The IP the result is for.
            result: The reputation dict to cache.
        """
        self._memory_cache[ip] = {
            "result": result,
            "fetched_at": datetime.now(timezone.utc),
        }

    def _get_cached(self, ip: str) -> dict | None:
        """Return a cached result if still within the TTL, else None.

        Args:
            ip: The IP to look up in the cache.

        Returns:
            The cached reputation dict (with ``source`` set to ``"cache"``), or
            ``None`` if absent or expired.
        """
        entry = self._memory_cache.get(ip)
        if entry is None:
            return None
        age = datetime.now(timezone.utc) - entry["fetched_at"]
        if age > timedelta(hours=self.cache_ttl_hours):
            return None
        cached = dict(entry["result"])
        cached["source"] = "cache"
        return cached

    def check_ip(self, ip: str) -> dict:
        """Look up an IP's reputation, using cache and failing gracefully.

        Args:
            ip: The IP address to check.

        Returns:
            A reputation dict::

                {
                    "ip": str,
                    "is_malicious": bool,
                    "abuse_score": int,      # 0-100 AbuseIPDB confidence
                    "country": str | None,
                    "isp": str | None,
                    "total_reports": int,
                    "source": str            # "cache" | "api" | "unavailable"
                }

            Private IPs, a missing API key, or any request failure all yield a
            neutral result (``is_malicious=False``, ``abuse_score=0``).
        """
        # Never look up private/internal addresses.
        if self._is_private_ip(ip):
            return _neutral_result(ip, source="unavailable")

        # No key => no external calls.
        if not self.api_key:
            return _neutral_result(ip, source="unavailable")

        cached = self._get_cached(ip)
        if cached is not None:
            return cached

        result = self._query_api(ip)
        # Only cache successful API results; transient failures should retry.
        if result["source"] == "api":
            self._cache_result(ip, result)
        return result

    def _query_api(self, ip: str) -> dict:
        """Perform the actual AbuseIPDB HTTP request.

        Args:
            ip: The IP to query.

        Returns:
            A reputation dict with ``source="api"`` on success, or a neutral
            result with ``source="unavailable"`` on any error/timeout.
        """
        query = urllib.parse.urlencode({"ipAddress": ip, "maxAgeInDays": 90})
        url = f"{self.ABUSEIPDB_URL}?{query}"
        request = urllib.request.Request(
            url,
            headers={"Key": self.api_key, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=_REQUEST_TIMEOUT_SECONDS
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            data = payload.get("data", {})
            abuse_score = int(data.get("abuseConfidenceScore", 0))
            return {
                "ip": ip,
                "is_malicious": abuse_score >= 50,
                "abuse_score": abuse_score,
                "country": data.get("countryCode"),
                "isp": data.get("isp"),
                "total_reports": int(data.get("totalReports", 0)),
                "source": "api",
            }
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return _neutral_result(ip, source="unavailable")

    def get_threat_points(self, ip: str) -> tuple[float, str | None]:
        """Convert an IP's reputation into risk points and an explanation.

        Banding:

        * abuse_score 0-25   -> 0 points (no reason).
        * abuse_score 26-50  -> +15 points, "IP flagged as suspicious".
        * abuse_score 51-75  -> +25 points, "IP has high abuse reports".
        * abuse_score 76-100 -> +40 points, "IP is known malicious".

        Args:
            ip: The IP address to evaluate.

        Returns:
            A ``(points, reason)`` tuple. ``reason`` is ``None`` when no points
            are awarded.
        """
        result = self.check_ip(ip)
        score = result.get("abuse_score", 0)

        if score <= 25:
            return 0.0, None
        if score <= 50:
            return 15.0, "IP flagged as suspicious"
        if score <= 75:
            return 25.0, "IP has high abuse reports"
        return 40.0, "IP is known malicious"
