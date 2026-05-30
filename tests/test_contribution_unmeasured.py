"""
test_contribution_unmeasured.py — the contribution slot stays honest.

The contribution recorder must NEVER return a self-generated score. It returns
UNMEASURED until an externally-anchored scorer is built. This test guards against
someone quietly slipping a proxy count into the slot (the demotion the whole
project is built to prevent).
"""

import os
import tempfile
from keava_owent.store.db import Store
from keava_owent.ledger.contribution import ContributionRecorder, VERDICT_HELPED


def _store():
    d = tempfile.mkdtemp()
    return Store(os.path.join(d, "t.sqlite"))


def test_contribution_is_unmeasured_not_zero():
    rec = ContributionRecorder(_store())
    out = rec.measure({"kind": "observe"}, {"status": "ok"})
    assert out["status"] == "UNMEASURED"   # never silently 0
    assert out["value"] is None
    assert out["unit"] is None


def test_human_verdict_is_recorded_externally():
    store = _store()
    rec = ContributionRecorder(store)
    v = rec.record_human_verdict("operator@example", VERDICT_HELPED, raw="great work")
    assert v["verdict"] == "helped"
    assert store.recent_verdicts()[0]["source"] == "operator@example"
