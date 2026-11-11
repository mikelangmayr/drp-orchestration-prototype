# 0008 — Polyglot primitive composition (ccdproc alongside PypeIt)

- Status: accepted
- Date: 2026-07-02

## Context

A predictable reviewer question is "why not just use PypeIt directly?" The answer
is that no single library has every primitive a multi-slit DRP needs in the form
we want, and the orchestration layer is what lets us assemble the best primitive
from each library under one DAG. That claim only holds if the codebase actually
composes primitives from more than one source. Until now every primitive was
PypeIt (trace) or custom (stub bias/dark, subtract).

## Decision

Add a real primitive sourced from **`ccdproc`** — an Astropy-coordinated package —
and compose it in the CAL DAG next to the PypeIt- and custom-sourced primitives:

- `core.combine_master_bias` median-combines a stack of real bias frames into a
  master, delegating to `ccdproc.combine`. It is wrapped to the `core` contract
  (numpy-in / numpy-out; the `CCDData` adaptation is internal). ccdproc returns a
  fresh `CCDData`, so — unlike PyReduce — no in-place-mutation refactor is needed.
- `combine_master_bias_task` wraps it (cached, like the other reproducible tasks).
- `cal_flow` gains a `bias_dir` option: given real bias frames it builds the
  master via ccdproc (discover → load → combine); otherwise it uses the constant
  pedestal stub. Either way the downstream subtract and the Quicklook PypeIt
  trace are unchanged — the flow is agnostic to which library a primitive came
  from.

The result: one Prefect DAG composing **ccdproc (bias) + custom (subtract/dark) +
PypeIt (trace)** — three sources — verified on the real LRIS-1 bias stack
(7 frames → master, median ≈ 1601 ADU).

## Why ccdproc

- Astropy-coordinated, so it also reinforces the abstract's Astropy-ecosystem
  framing claim (two birds).
- Clean functional API and no in-place mutation → integrates without a refactor.
- Easy, reliable install (vs. PyReduce's C library).

## Scope note — this is NOT claim 4

Polyglot composition (which *library* a primitive comes from) is distinct from
the dual-layer primitive model (claim 4: our own primitives get a pure-Python
reference plus an optional compiled-C backend, for speed). Claim 4 remains
parked. ccdproc does not demonstrate it.

## Consequences

- `ccdproc==2.5.1` pinned in the main dependencies (it pulls a sizable transitive
  tree — scikit-image, dask-image, zarr — accepted as the cost of a real
  Astropy-ecosystem primitive).
- The stub bias path stays for the synthetic LRIS-2 flats (no real biases at that
  detector shape); the ccdproc path activates with a real bias directory. Fully
  wiring ccdproc bias into a real end-to-end LRIS reduction awaits the multi-amp
  raw loader (parked) so shapes match through the trace.

## Alternatives rejected / deferred

- **PyReduce** (the plan's originally-named choice): a spectroscopic package, so
  a stronger "compose two spectroscopic pipelines" story and an upstream-
  contribution target (§9). Deferred: it ships a C library to build and has
  in-place-mutation steps needing a functional wrapper. A good candidate for a
  *second* polyglot primitive later.
