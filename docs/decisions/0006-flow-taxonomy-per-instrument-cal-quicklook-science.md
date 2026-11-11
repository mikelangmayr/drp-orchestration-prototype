# 0006 — Separate flows per instrument; CAL / Quicklook / Science triad

- Status: accepted
- Date: 2026-06-30

(ADR numbers 0004 and 0005 are reserved by reference in other docs for the
canonical data model and the numpy cache fingerprint; this decision takes 0006.)

## Context

The prototype now holds real data from two instruments — LRIS and DEIMOS — plus
the synthetic LRIS-2 proxy. Their raw formats differ fundamentally (LRIS
single-HDU vs DEIMOS 16-HDU multi-amplifier), as do detector geometry,
calibration sets, and PypeIt spectrograph definitions. A single parameterized
DRP spanning both would degenerate into pervasive `if instrument == …` branching
— the opposite of the readable wiring diagram the architecture requires.

Separately, a DRP serves three operating purposes with different speed/quality
tradeoffs: building calibrations, real-time quick-look, and full science-quality
reduction.

## Decision

Organize flows as a matrix of **instrument × purpose**. Per instrument, three
DAGs:

- **CAL DAG.** Builds and caches the master calibrations (master bias, master
  flat, wavelength solution) for each configuration group. This is where the
  parallel calibration arms of ADR 0003 live. In real-time mode it pre-processes
  calibrations as they arrive; in reprocessing it runs on demand. Its outputs are
  cached and reused.
- **Quicklook DAG.** Fast, fixed-parameter reduction for real-time observing:
  2D wavelength-calibrated, sky-subtracted frames with fixed-boxcar 1D
  extraction. Consumes the CAL masters as cache hits.
- **Science DAG.** Full science-quality reduction: optimal extraction, local +
  global sky models, flux calibration. Consumes the same CAL masters.

Rules that follow:

- **Instruments get separate flow modules** (`flows/<instrument>/{cal,
  quicklook,science}`). They do not share a DAG.
- **They do share `core/` primitives and `tasks/` wrappers** wherever the
  algorithm is instrument-general (tracing, bias subtraction, flat
  normalization, extraction, wavelength calibration). Instrument differences are
  confined to the raw loader/preprocessor (amplifier assembly, orientation) and
  the spectrograph/config parameters. Only orchestration is split, not science.
- **The no-Red/Blue-fork rule still holds within an instrument.** Channel and
  configuration are parameters, not separate flows.
- **CAL → {Quicklook, Science} is the cross-DAG caching edge.** Masters built
  once by CAL are served from cache to both consumers — directly the selective
  re-execution (claim 2) and parallelism (claim 3) story.

## Relationship to the abstract's example flows

The paper's Flow A / B / C (happy path, selective re-execution, graceful failure)
are **demonstrations of claims, not instrument flows**. They are scenarios run
against the real DAGs: e.g. selective re-execution shown by changing a parameter
in the Science DAG and watching CAL masters serve from cache; graceful failure
shown on a Quicklook batch with one corrupt frame. The triad is the structure;
A / B / C are what we demonstrate with it.

## Consequences

- `flows/` restructures into per-instrument subpackages. The current
  `flows/reduce.py` (the Flow A seed) and `flows/tracing.py` fold into the
  LRIS CAL and Quicklook DAGs.
- The multi-amplifier loader (parked) is the precondition for the DEIMOS
  instrument flows; the LRIS flows can proceed now (single-HDU /
  synthetic load today).
- Shared primitives keep the polyglot and upstream-contribution story intact;
  the per-instrument split is purely at the orchestration layer.
- `docs/architecture.md` §"Flow composition" is updated to describe the triad;
  that drift is resolved as part of this ADR.

## Alternatives rejected

- **Single parameterized cross-instrument DRP.** Collapses under format and
  geometry differences into unreadable branching; confirmed infeasible.
- **One flow per (instrument, channel).** Violates the no-Red/Blue-fork rule;
  channel is a parameter within an instrument's flows.
