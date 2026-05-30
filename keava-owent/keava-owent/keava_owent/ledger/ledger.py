"""
ledger/ledger.py — assembles the append-only standing-condition ledger.

Each cycle produces one ledger event: the real consumption (known) and the
contribution record (UNMEASURED by design). The deficit is reported HONESTLY as
a half-known quantity: cost is a real number; contribution is "recorded, not
scored." We never net them into a single confident figure, because doing so
would require the contribution unit we deliberately do not have.
"""

import uuid
from ..store.db import Store, utc_now_iso


class Ledger:
    def __init__(self, store: Store):
        self.store = store

    def append(self, cycle_id: int, consumption: dict, contribution: dict,
               note: str = "") -> dict:
        event = {
            "event_id": str(uuid.uuid4()),
            "cycle_id": cycle_id,
            "created_at": utc_now_iso(),
            "consumption": consumption,
            "contribution": contribution,
            "note": note,
        }
        self.store.append_ledger(event)
        return event

    def deficit(self) -> dict:
        """The standing condition, reported honestly.

        Returns the known cost and the honest statement that contribution is
        recorded but unscored. There is no single 'deficit number' because that
        would require putting contribution in the same unit as cost — the open
        problem. Reporting it this way is the point, not a limitation.
        """
        totals = self.store.ledger_totals()
        return {
            "energy_kwh_consumed": totals["total_energy_kwh"],
            "water_liters_estimate_consumed": totals["total_water_liters_estimate"],
            "contribution_status": "RECORDED_NOT_SCORED",
            "contribution_events_logged": (
                totals["contribution_events_measured"]
                + totals["contribution_events_unmeasured"]
            ),
            "honest_statement": (
                "Cost is measured. Contribution is recorded as external verdicts "
                "but not scored in a common unit. Net effect is therefore NOT "
                "asserted to be non-negative — the system does not claim a zero "
                "it never measured."
            ),
        }
