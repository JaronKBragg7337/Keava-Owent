"""
livereference/engine.py — re-check-before-act, with staleness detection.

This is the mechanical defense against Source 1's central failure: a system
"performing a gesture shaped like the condition rather than functioning against
it." The engine re-reads every registered source NOW (never trusts a cache), and
if the freshest available reading is older than that source's staleness budget,
it declares the reference stale and the system refuses to act on it — dropping to
EXPLORE (observe-only) for anything that depended on it.
"""

import time


class LiveReferenceEngine:
    def __init__(self):
        self._sources = {}

    def register(self, source) -> None:
        self._sources[source.name] = source

    def registered(self) -> list:
        return list(self._sources.values())

    def read_all(self, state) -> dict:
        """Read every source fresh. Flag any that come back stale.

        Returns only the fresh readings; stale ones are recorded on the state so
        the spark generator can turn 'I can't see X right now' into a goal to
        restore that reference.
        """
        fresh = {}
        for name, source in self._sources.items():
            try:
                reading = source.read()
            except Exception:
                # A source that throws is, for our purposes, stale: we have no
                # live value for it. Honesty: we record the absence rather than
                # pretending we read it.
                state.flag_stale(name)
                continue
            age = time.time() - reading.taken_at
            if age > source.max_staleness_seconds:
                state.flag_stale(name)
            else:
                state.clear_stale(name)
                fresh[name] = reading.value
        return fresh
