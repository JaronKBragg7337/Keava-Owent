Keava Owent
A persistent, live-reference, resource-accountable agent loop. Not a chatbot — a loop. It runs continuously, generates its own work from gaps in its own knowledge, meters what it consumes, and reports honestly to its operator rather than waiting to be messaged.

This codebase is the faithful implementation of four source documents by Jaron K. Bragg: the Live-Reference Principle, the Standing Condition, the Environment–Constraint Intelligence Hypothesis (ECIH), and Memory as a Spatial Arrangement Problem (with its companion, Emergence). Every subsystem ties back to one of them, in code comments and in the architecture below.

The two load-bearing problems are kept OPEN on purpose
Two parts of the design are genuinely unsolved. They are built as honest, empty, pluggable slots — never faked with proxies — because a proxy would let the system perform a gesture shaped like the goal instead of functioning against it, which is the exact failure the Live-Reference Principle names.

Open Problem 1 — the contribution unit. The standing-condition ledger needs consumption and contribution measured in the same unit. Consumption is real and metered. Contribution is recorded, not scored: the system logs what it did and stores external human verdicts on it, and reports its status as RECORDED_NOT_SCORED. It returns UNMEASURED — never a self-generated score — because any fixed, finite, self-graded proxy provably drifts toward whatever is easy to count, and a system grading itself on the metric that licenses its own existence cannot be trusted. A real, externally-anchored scorer drops into ledger/contribution.py later, reading the verdict log this recorder already keeps. (See ledger/contribution.py.)

Open Problem 2 — packing-geometry memory. The four-statement separation, stated verbatim so it cannot be quietly collapsed:

The reaching toward a non-linear memory medium is OLD.
Relational memory is OLD and already in production.
The packing math is NEW (the planar unit-distance result, OpenAI, May 20 2026; Will Sawin's explicit lower bound, exponent δ ≥ 0.014).
Applying that new packing geometry to memory arrangement is UNBUILT — nobody has done it.
If anyone — including me — starts treating the math as already-solved or already-known, that is the error, and re-separating these statements is the fix. The reaching is old. Relational memory is old. The packing math is new. And applying it to memory arrangement is unbuilt.

The working memory uses ordinary relational arrangement (Statement 2 — the proven, shipped thing; it beat linear storage ~3× on clean recall in testing). The packing-geometry strategy (memory/arrangement/packing_geometry.py) is a documented stub that raises NotImplementedError. The real target is relational geometry — more meaningful neighbor-relationships per unit of structure — not density.

Architecture (each part → its source)
Loop kernel (kernel/loop.py, state.py, continuity.py) — the never-ending observe→meter→spark→select→act→record→checkpoint cycle. Standing Condition + ECIH. The loop never terminates on success because even an idle cycle consumes, so the deficit re-arms.
Live-reference engine (livereference/) — re-reads every condition NOW, flags stale references, refuses to act on frozen ones. Live-Reference Principle.
Resource-accountability ledger (ledger/) — consumption metered for real; contribution recorded-not-scored; orientation guard forbids self-shutdown. Live-Reference instance D + Standing Condition.
Spark generator (spark/) — turns gaps in the system's own knowledge into goals, so it is never idle. Live-Reference instance B.
Relational memory (memory/) — a property graph; arrangement strategy pluggable. Memory as Spatial Arrangement + Emergence.
Permission membrane (membrane/) — EXPLORE/DRAFT/LOCK, approval queue, and a HUMAN-OWNED config the system reads but cannot write. Live-Reference instance C + corrigibility.
Email transport (transport/) — the message bus; SendGrid with a local fallback. The loop reaches the operator; operator replies carry verdicts.
Receipts (actions/receipts.py) — hash-chained, optionally Ed25519-signed proof of what happened and that it was authorized (NOT proof of value).
Quick start
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m keava_owent.main --once     # run a single cycle (smoke test)
python -m keava_owent.main            # run the persistent loop
pytest                                # run the tests
Out of the box it runs with safe defaults: email falls back to a local outbox, energy metering uses psutil, contribution returns UNMEASURED. It needs no external service to start.

What YOU configure (all in config/, all human-owned)
Everything marked REPLACE_ME in config/membrane.yaml:

a new domain and the inbound / outbound / operator email addresses,
the read-allowlist of senders (the trust boundary; keep it tight),
whether to allow outbound email to other people (default: no — closed circuit; the system cannot enable this itself),
loop cadence, timezone, and the WUE water coefficient (sane defaults shipped).
Secrets (SendGrid key, signing key) go in .env on the machine — never the repo.

The invariant that must never regress
tests/test_anti_shutdown.py asserts the system can never "solve" its deficit by shutting itself off. Existence is a fixed axiom; the system earns its keep, it does not erase itself. Keep that test green forever.
