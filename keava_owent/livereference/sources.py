"""
livereference/sources.py — registered live conditions and their staleness budgets.

The Live-Reference Principle (Source 1) says a reference is only valid while it
stays connected to the live condition it points at. To enforce that, every
external condition the system relies on is registered here WITH a max_staleness:
how old a reading may be before it counts as frozen.

A LiveSource is just a name, a read function, and a staleness budget in seconds.
The consumption meter is itself registered as a live source — so a cycle that
fails to meter is structurally unable to claim 'no harm,' which is instance D.
"""

import time
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Reading:
    source: str
    value: Any
    taken_at: float  # epoch seconds


@dataclass
class LiveSource:
    name: str
    read_fn: Callable[[], Any]
    max_staleness_seconds: float

    def read(self) -> Reading:
        return Reading(self.name, self.read_fn(), time.time())
