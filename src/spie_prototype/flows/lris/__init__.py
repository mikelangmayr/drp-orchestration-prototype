"""LRIS instrument flow triad (ADR 0006).

Three DAGs for the LRIS instrument (LRIS-1 data, plus synthetic LRIS-2 stand-in flats):

- ``cal`` — CAL DAG: build and cache master calibrations.
- ``quicklook`` — Quicklook DAG: fast, fixed-parameter, real-time reduction.
- ``science`` — Science DAG: full science-quality reduction (placeholder).

Quicklook and Science consume the CAL DAG's cached masters. Instruments do not
share a DAG; they share ``core``/``tasks`` where the algorithm is general.
"""
