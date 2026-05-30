"""
main.py — assembly and start.

This wires every subsystem together and starts the never-ending loop on a
schedule. It is the only file that knows about all the pieces at once; each
subsystem stays ignorant of the others except through the small interfaces the
loop passes in. That separation is deliberate — it keeps the two OPEN slots
(contribution scorer, packing-geometry arrangement) swappable without touching
anything else.

Run it with:  python -m keava_owent.main
Or once, for a smoke test:  python -m keava_owent.main --once
"""

import os
import sys
import time
import yaml

from .store.db import Store
from .kernel.continuity import Continuity
from .kernel.loop import Loop
from .livereference.engine import LiveReferenceEngine
from .livereference.sources import LiveSource
from .ledger.consumption import ConsumptionMeter
from .ledger.contribution import ContributionRecorder
from .ledger.ledger import Ledger
from .memory.graph import MemoryGraph
from .memory.recall import Recall
from .spark.generator import SparkGenerator
from .membrane.modes import Membrane
from .membrane.approval import ApprovalQueue
from .actions.receipts import ReceiptLog
from .transport.email_transport import EmailTransport


def _load_yaml(path: str, default: dict) -> dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or default
    return default


def build(config_dir: str = "config", data_dir: str = "data") -> Loop:
    # The membrane config is HUMAN-OWNED. We read it; we never write it.
    membrane_cfg = _load_yaml(os.path.join(config_dir, "membrane.yaml"), {})
    wue_cfg = _load_yaml(os.path.join(config_dir, "wue_coefficient.yaml"),
                        {"liters_per_kwh": 1.8, "basis": "industry_onsite_average_LBNL_2016"})
    limits_cfg = _load_yaml(os.path.join(config_dir, "limits.yaml"),
                           {"cadence_seconds": 1800})

    store = Store(os.path.join(data_dir, "keava_owent.sqlite"))

    continuity = Continuity(store)
    meter = ConsumptionMeter(
        wue_liters_per_kwh=wue_cfg.get("liters_per_kwh", 1.8),
        wue_label=wue_cfg.get("basis", "unspecified"),
    )
    ledger = Ledger(store)
    contribution = ContributionRecorder(store)

    memory = MemoryGraph(os.path.join(data_dir, "memory_graph.json"))
    recall = Recall(memory)
    spark = SparkGenerator(recall)

    membrane = Membrane(membrane_cfg)
    approvals = ApprovalQueue(store)

    # Optional Ed25519 signing key for receipts, from the environment (never repo).
    signing_pem = os.environ.get("KEAVA_RECEIPT_SIGNING_KEY_PEM")
    receipts = ReceiptLog(store, signing_pem.encode() if signing_pem else None)

    transport = EmailTransport(membrane_cfg.get("email", {}))

    # The live-reference engine. The consumption meter is itself a live source:
    # a cycle that cannot read its own draw is, by instance D, unable to claim
    # 'no harm'. We register a heartbeat source so staleness has something to
    # watch even on a fresh install.
    live_engine = LiveReferenceEngine()
    live_engine.register(LiveSource(
        name="heartbeat",
        read_fn=lambda: time.time(),
        max_staleness_seconds=limits_cfg.get("cadence_seconds", 1800) * 3,
    ))

    return Loop(
        continuity=continuity, live_engine=live_engine, meter=meter,
        ledger=ledger, contribution=contribution, memory=memory, recall=recall,
        spark=spark, membrane=membrane, approvals=approvals, receipts=receipts,
        transport=transport, config={"limits": limits_cfg},
    )


def main():
    once = "--once" in sys.argv
    loop = build()

    if once:
        out = loop.cycle()
        print("cycle complete:")
        for k, v in out.items():
            print(f"  {k}: {v}")
        return

    # The persistent schedule. APScheduler keeps the cadence and (with a
    # persistent jobstore, configured for production) survives restarts. For the
    # skeleton we run a simple blocking scheduler; the loop's own state is what
    # actually persists across restarts, via the durable store.
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except Exception:
        # If APScheduler isn't installed, fall back to a plain sleep loop so the
        # system still runs. Graceful degradation, labeled.
        cadence = loop.config["limits"].get("cadence_seconds", 1800)
        print(f"[no apscheduler] running plain loop every {cadence}s")
        while True:
            loop.cycle()
            time.sleep(cadence)

    cadence = loop.config["limits"].get("cadence_seconds", 1800)
    sched = BlockingScheduler()
    sched.add_job(loop.cycle, "interval", seconds=cadence, id="keava_owent_cycle",
                 max_instances=1, coalesce=True)
    print(f"Keava Owent loop started — every {cadence}s. Ctrl-C to stop.")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("Loop stopped. State is checkpointed; restart resumes cleanly.")


if __name__ == "__main__":
    main()
