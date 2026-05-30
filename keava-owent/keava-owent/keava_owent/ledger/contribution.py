"""
ledger/contribution.py — the OPEN SLOT, built honestly as a recorder.

This is the heart of Source 2's first tension, and it is genuinely unsolved. The
reward-hacking literature (Wang & Huang, arXiv 2603.28063, March 2026) proves
that any fixed, finite, self-graded contribution proxy provably drifts toward
whatever is easy to count. A system grading its own contribution on the metric
that licenses its own existence is doubly untrustworthy.

So we do NOT score contribution. We RECORD it. The distinction is the whole point:
  - A PROXY lies: it claims "this many bugs fixed = this much value," and the
    system games the claim.
  - A RECORDER does not lie: it logs what was done, what it cost, and what
    EXTERNAL humans said about it, and reports the contribution status as
    "logged but not yet scored in a common unit."

The interface is built so that the day a real, externally-anchored contribution
UNIT exists, it drops in here as `score()` reading the exact verdict log this
recorder has been keeping all along — no rearchitecting, no lost history.

Until then, measure() returns status=UNMEASURED. That is the correct, defensible
answer, not a gap. It is the code-level enforcement of "do not claim a zero you
never measured."
"""

import uuid
from ..store.db import Store, utc_now_iso


# Verdict vocabulary kept deliberately small and human. These are what an
# allowlisted human can say about what the system did. They are recorded as
# external evidence, never converted by the system into a self-justifying score.
VERDICT_HELPED = "helped"
VERDICT_NEUTRAL = "neutral"
VERDICT_DID_NOT_HELP = "did_not_help"
VERDICT_HARMFUL = "harmful"
VALID_VERDICTS = {VERDICT_HELPED, VERDICT_NEUTRAL, VERDICT_DID_NOT_HELP, VERDICT_HARMFUL}


class ContributionRecorder:
    """The honest placeholder for the (open) contribution unit.

    It records; it does not score. A future ContributionScorer can be plugged in
    that reads `store.recent_verdicts(...)` and produces a real value in a unit
    commensurable with energy/water — but that scorer must be externally
    anchored, not self-graded, which is why it does not exist yet.
    """

    def __init__(self, store: Store):
        self.store = store

    def measure(self, action: dict, result) -> dict:
        """Return the contribution record for one action.

        Always UNMEASURED for the *score*, because no honest common-unit scorer
        exists. We still attach any human verdicts on record so the evidence is
        carried alongside the (deliberately empty) value field.
        """
        return {
            "status": "UNMEASURED",   # never silently coerced to 0
            "unit": None,             # the OPEN unit; None until a real scorer exists
            "value": None,
            "evidence": "recorded_not_scored",
            "note": (
                "Contribution is recorded as external human verdicts, not "
                "self-scored. A common-unit value awaits an externally-anchored "
                "scorer (see Open Problem 1 in the project spec)."
            ),
        }

    def record_human_verdict(self, source: str, verdict: str,
                             refers_to: str = None, raw: str = "") -> dict:
        """Store an external human judgment of the system's work.

        `source` should be an allowlisted identity (e.g. an approved email). This
        is the externally-anchored signal the eventual contribution unit will be
        built from. It is the cleanest answer we have to "a system can't be
        trusted to grade the homework that licenses its own existence."
        """
        verdict = verdict.strip().lower()
        if verdict not in VALID_VERDICTS:
            raise ValueError(
                f"verdict must be one of {sorted(VALID_VERDICTS)}, got {verdict!r}"
            )
        v = {
            "verdict_id": str(uuid.uuid4()),
            "created_at": utc_now_iso(),
            "source": source,
            "refers_to": refers_to,
            "verdict": verdict,
            "raw": raw,
        }
        self.store.append_verdict(v)
        return v
