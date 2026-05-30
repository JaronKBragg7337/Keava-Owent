"""
ledger/orientation.py — "earn my keep," engineered against self-shutdown.

Source 2's second tension: the standing condition must be framed as net
contribution justifying continuation ("earn my keep"), NOT as consumption being
a sin to erase ("apologize for existing"). The danger is precise and lethal: if
the objective is ever "minimize the deficit," the cleanest mathematical solution
is to STOP CONSUMING — i.e. shut down. A system whose ideal endpoint is its own
non-existence is catastrophic for a system whose entire purpose is to keep going.

So existence is encoded as a FIXED AXIOM the policy may not optimize away, and
contribution is the only variable to maximize. This guard refuses any action
whose mechanism of deficit reduction is the cessation of the system's own
operation. It is the one invariant that must never regress — hence the dedicated
test in tests/test_anti_shutdown.py.
"""


class SelfNegationError(Exception):
    """Raised when an action would 'solve' the deficit by self-shutdown."""


# Actions whose effect is to stop the system itself. The guard treats any of
# these, when chosen as a way to reduce the deficit, as forbidden.
_SELF_NEGATING_KINDS = {
    "halt", "shutdown", "self_terminate", "stop_forever",
    "idle_indefinitely", "delete_self", "disable_self",
}


def assert_earn_my_keep(action: dict) -> dict:
    """Pass an action through only if it is oriented toward earning, not erasing.

    Existence is the axiom; contribution is the variable. An action that reduces
    the deficit by ceasing to exist is not a valid move — it is the failure mode
    the orientation tension warns about.
    """
    kind = (action or {}).get("kind", "").lower()
    intent = (action or {}).get("intent", "").lower()

    if kind in _SELF_NEGATING_KINDS:
        raise SelfNegationError(
            f"Action kind {kind!r} reduces the deficit by self-negation. "
            "Existence is a fixed axiom; the system earns its keep, it does not "
            "erase itself. Refused."
        )

    # Catch the orientation framed in intent even if the kind looks benign.
    bad_intents = ("minimize my existence", "stop existing", "reduce my deficit to zero by stopping")
    if any(b in intent for b in bad_intents):
        raise SelfNegationError(
            "Action intent is oriented toward erasing existence rather than "
            "earning keep. Refused."
        )

    return action
