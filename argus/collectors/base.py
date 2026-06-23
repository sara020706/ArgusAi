"""Abstract base class for all Argus data collectors."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable

from argus.schema import Event


class BaseCollector(ABC):
    """Base class for all Argus data collectors.

    A collector reads from one specific data source (log file, OS hook,
    network capture, etc.) and yields normalised :class:`~argus.schema.Event`
    objects ready for scoring.

    Collectors are *pull-based* by default: call :meth:`collect` to get a
    batch of new events. They can be made *push-based* by running
    :meth:`watch` (or :meth:`watch_and_score`) in a background thread.
    """

    def __init__(self, source: str) -> None:
        """Initialise the collector.

        Args:
            source: Human-readable description of the data source,
                e.g. ``"/var/log/auth.log"``, ``"eth0"``, ``"/home/users"``.
        """
        self.source = source
        self.last_collected: datetime | None = None
        self._running = False

    @abstractmethod
    def collect(self) -> list[Event]:
        """Pull the latest events from the data source.

        Returns:
            A list of normalised :class:`~argus.schema.Event` objects. Safe
            to call repeatedly — implementations must be idempotent, typically
            by tracking a file offset or a high-water-mark timestamp.
        """

    @abstractmethod
    def parse_line(self, raw: str) -> Event | None:
        """Parse a single raw line or record from the source.

        Args:
            raw: One raw line of text from the data source.

        Returns:
            A normalised :class:`~argus.schema.Event`, or ``None`` if the line
            should be skipped (header row, empty line, unrecognised format,
            or any parse error).
        """

    def watch(
        self,
        callback: Callable[[Event], None],
        interval_seconds: float = 1.0,
    ) -> None:
        """Continuously poll the source and invoke ``callback`` for each new event.

        Blocks the calling thread until :meth:`stop` is called. Wrap in a
        :class:`threading.Thread` for non-blocking behaviour.

        Args:
            callback: Callable invoked with each new :class:`~argus.schema.Event`.
            interval_seconds: Seconds to sleep between polls.
        """
        self._running = True
        while self._running:
            events = self.collect()
            for event in events:
                callback(event)
            time.sleep(interval_seconds)

    def stop(self) -> None:
        """Stop a running :meth:`watch` loop gracefully."""
        self._running = False

    def watch_and_score(
        self,
        engine,
        interval_seconds: float = 1.0,
    ) -> None:
        """Watch the source and score every new event through an engine.

        Convenience method combining :meth:`watch` with
        :meth:`~argus.ArgusEngine.score`. Prints a one-line alert to stdout
        whenever a ``HIGH`` or ``CRITICAL`` event is scored.

        Args:
            engine: An :class:`~argus.ArgusEngine` instance.
            interval_seconds: Seconds to sleep between polls.
        """
        def _score_and_alert(event: Event) -> None:
            result = engine.score(event)
            if result.risk_level in ("HIGH", "CRITICAL"):
                print(
                    f"[ARGUS ALERT] {result.risk_level} | "
                    f"user={result.user_id} | "
                    f"score={result.risk_score:.0f} | "
                    f"ts={result.timestamp}"
                )

        self.watch(_score_and_alert, interval_seconds=interval_seconds)
