# 0002 — Pin PypeIt to 1.18.1

- Status: accepted
- Date: 2026-06-29

## Context

The slit-tracing primitive (`core/tracing.py`) depends on PypeIt internals that
are not part of a stable public API: `EdgeTraceSet`, `EdgeTracePar`,
`TraceImage`, and the `traceid` sign convention for left/right edges. These can
shift between PypeIt releases. The paper must cite the exact version used.

## Decision

Pin `pypeit==1.18.1` in `pyproject.toml` (the version installed and verified in
this environment). `core/tracing.py` carries a module-level check that emits a
`RuntimeWarning` when the imported version differs, rather than a hard assert —
so a compatible patch release does not block notebook or CI use, but drift is
never silent.

## Consequences

- Reproducibility across environments (a framing commitment of the abstract):
  the same pinned version yields the same tracing behavior anywhere.
- A future `trace_from_array()` upstream contribution to PypeIt would let us
  depend on a stable entry point and relax the version sensitivity.

## Alternatives rejected

- **Float to latest PypeIt.** Maximizes freshness but risks silent behavior
  changes in unpinned internals between paper runs.
- **Hard version assert.** Too brittle; blocks compatible patch releases and
  harms the notebook/test ergonomics the layering exists to protect.
