"""Storage backends for Argus.

Exposes the abstract :class:`ArgusStore` interface and the two bundled
implementations: :class:`SQLiteStore` (persistent, zero-setup default) and
:class:`MemoryStore` (in-process, for tests and externally-persisted apps).
"""

from argus.storage.base import ArgusStore
from argus.storage.sqlite_store import SQLiteStore
from argus.storage.memory_store import MemoryStore

__all__ = ["ArgusStore", "SQLiteStore", "MemoryStore"]
