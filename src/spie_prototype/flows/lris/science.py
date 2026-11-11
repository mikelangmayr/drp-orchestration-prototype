"""LRIS Science DAG: full science-quality reduction (placeholder).

The science arm of the LRIS flow triad (ADR 0006). It consumes the same CAL
masters as the Quicklook DAG but adds optimal extraction (PypeIt models),
local + global sky models, and flux calibration. Those primitives are not
implemented yet; this module reserves the structure so the triad is complete and
the dependency on the CAL DAG is explicit.
"""
from __future__ import annotations

from prefect import flow


@flow(name="LRIS Science")
def science_flow(input_dir: str, output_dir: str) -> None:
    """Placeholder for the full science-quality reduction.

    Raises
    ------
    NotImplementedError
        Always — the optimal-extraction, sky-model, and flux-calibration
        primitives are pending. When added, this DAG consumes the same CAL
        masters as :func:`spie_prototype.flows.lris.quicklook.quicklook_flow`.
    """
    raise NotImplementedError(
        "LRIS Science DAG is not implemented yet: optimal extraction, sky model, "
        "and flux calibration primitives are pending. It will consume the same CAL "
        "masters as the Quicklook DAG (ADR 0006)."
    )
