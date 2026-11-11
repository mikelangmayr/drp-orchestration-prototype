# 0003 — Parallel calibration arms via master construction

- Status: accepted
- Date: 2026-06-29

## Context

Phase 3 ("DAG shape for Flow A") had two source docs that described the
calibration DAG differently:

- `docs/plan.md` item 10: "discover → (bias ∥ dark ∥ flat-prep) → join → trace …
  the dashboard should show parallel calibration arms."
- `docs/architecture.md` §"Canonical flow shape": a per-frame chain
  `bias_subtract(raw) → dark_subtract(...) → trace`, *sequential within a frame*,
  with parallelism coming only from running frames concurrently.

Taken literally, the plan implies bias and dark act as independent parallel arms
on the same raw frame and are then "joined" — which is not how reduction works
(bias and dark subtraction are sequential on a single frame, and joining two
separately-corrected copies of one frame is scientifically meaningless). The
architecture doc's sequential shape is physically honest but shows no parallel
calibration arms, which the abstract (claim 3, "calibration fan-out") calls for.

## Decision

Realize the parallel calibration arms as **independent master-construction
tasks**, not as parallel per-frame subtraction:

- `make_master_bias_task` and `make_master_dark_task` take no shared input, so
  the flow submits both and they run concurrently — genuine parallel arms,
  visible on the dashboard.
- Each master is cached and reused across every frame and every re-run (masters
  are reusable across all mask designs — the canonical caching story).
- Per frame, application stays sequential as the architecture doc requires:
  `subtract_bias(frame, master_bias) → subtract_dark(…, master_dark) → trace`.
  Each frame's chain *joins* both arms at the subtract steps.
- Frames fan out concurrently across the batch.

Phase 3 ships the masters as **stubs** (constant pedestals; test data is flats +
arcs only). The subtract primitives are real array ops, so the Phase 7 swap to
PyReduce / ccdproc master combination changes no flow or task wiring.

## Consequences

- The DAG is physically honest *and* shows parallel arms — both docs are now
  satisfiable without distortion.
- Sets up Phase 4 (caching / Flow B): the master arms are the natural cache-hit
  demonstration when a downstream trace parameter changes.
- `docs/architecture.md` §"Canonical flow shape" is updated to match this shape;
  that drift is resolved as part of this ADR.

## Alternatives rejected

- **Literal `(bias ∥ dark) → join` on one raw frame.** Matches the plan's words
  but encodes a scientifically wrong DAG into a paper whose thesis is honesty of
  architecture. Rejected.
- **Sequential only, parallelism from frame fan-out alone.** Honest but omits the
  calibration-arm parallelism the abstract names. Kept the fan-out *and* added
  the arms.
