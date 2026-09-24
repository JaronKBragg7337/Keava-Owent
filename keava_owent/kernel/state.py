"""
kernel/state.py — the internal state the system regulates.

ECIH (Source 3) defines intelligence as the capacity to maintain, regulate, and
adapt internal state under constraint. This dataclass IS that internal state.
It is small on purpose: a system that has to hold a coherent picture of itself
across restarts is better served by a tight, well-understood state than a sprawl
of fields nobody can reason about.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from ..store.db import utc_now_iso


# The three operating modes are the permission membrane's coarse setting.
# EXPLORE is always safe (observe/propose only) and is the fallback whenever the
# system is uncertain or a reference has gone stale.
MODE_EXPLORE = "EXPLORE"
MODE_DRAFT = "DRAFT"
MODE_LOCK = "LOCK"

HEALTH_NOMINAL = "NOMINAL"
HEALTH_DEGRADED = "DEGRADED"
HEALTH_RECOVERING = "RECOVERING"


@dataclass
class InternalState:
    cycle_id: int = 0
    timestamp: str = field(default_factory=utc_now_iso)
    mode: str = MODE_EXPLORE
    # Gaps in the system's own knowledge. These ARE the spark (Source 1,
    # instance B): the not-knowing is what generates the next goal, so the
    # system never sits idle waiting for a human to hand it a task.
    open_gaps: list = field(default_factory=list)
    active_goal: Optional[dict] = None
    health: str = HEALTH_NOMINAL
    last_checkpoint: Optional[str] = None
    # Flagged stale references (Live-Reference). If a source is in here, the
    # system refuses to act on it until it reads fresh.
    stale_sources: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "InternalState":
        if not d:
            return cls()
        known = {k: d[k] for k in cls().to_dict().keys() if k in d}
        return cls(**known)

    def flag_stale(self, source_name: str) -> None:
        if source_name not in self.stale_sources:
            self.stale_sources.append(source_name)

    def clear_stale(self, source_name: str) -> None:
        if source_name in self.stale_sources:
            self.stale_sources.remove(source_name)
