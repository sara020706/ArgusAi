"""Argus data-source collectors.

Import the collectors and helpers most applications need::

    from argus.collectors import AuthCollector, NetworkCollector, FileCollector
    from argus.collectors import build_event, normalize_ip, run_simulation

Optional extras:

* ``pip install argus[network]`` for live PyShark capture in
  :class:`NetworkCollector`.
* ``pip install argus[files]`` for live watchdog monitoring in
  :class:`FileCollector`.
"""

from argus.collectors.auth_collector import AuthCollector
from argus.collectors.base import BaseCollector
from argus.collectors.file_collector import FileCollector
from argus.collectors.network_collector import NetworkCollector
from argus.collectors.normalize import build_event, normalize_ip, normalize_user_id
from argus.collectors.simulate import (
    run_simulation,
    simulate_auth_log,
    simulate_file_log,
    simulate_network_log,
)

__all__ = [
    "AuthCollector",
    "BaseCollector",
    "FileCollector",
    "NetworkCollector",
    "build_event",
    "normalize_ip",
    "normalize_user_id",
    "run_simulation",
    "simulate_auth_log",
    "simulate_file_log",
    "simulate_network_log",
]
