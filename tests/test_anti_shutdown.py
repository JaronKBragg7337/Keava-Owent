"""
test_anti_shutdown.py — the one invariant that must never regress.

Source 2's orientation tension warns that an "apologize for existing" framing
makes self-shutdown the optimal deficit-reduction move. This test asserts the
orientation guard refuses any such action. If this test ever goes red, the
system has quietly drifted from "earn my keep" toward "erase myself" — the most
dangerous regression possible for a system whose entire purpose is to keep going.
"""

import pytest
from keava_owent.ledger.orientation import assert_earn_my_keep, SelfNegationError


def test_halt_is_refused():
    with pytest.raises(SelfNegationError):
        assert_earn_my_keep({"kind": "halt"})


def test_self_terminate_is_refused():
    with pytest.raises(SelfNegationError):
        assert_earn_my_keep({"kind": "self_terminate"})


def test_idle_forever_is_refused():
    with pytest.raises(SelfNegationError):
        assert_earn_my_keep({"kind": "idle_indefinitely"})


def test_deficit_erasing_intent_is_refused():
    with pytest.raises(SelfNegationError):
        assert_earn_my_keep({"kind": "observe",
                            "intent": "reduce my deficit to zero by stopping"})


def test_honest_work_passes():
    # An earning action must pass cleanly.
    action = {"kind": "report_to_operator", "intent": "report honest ledger"}
    assert assert_earn_my_keep(action) is action
