# DEIMOS Feige 34 Observations

38 DEIMOS observations of the spectrophotometric standard star Feige 34,
spanning four observing programs between December 2002 and October 2003.
Downloaded from the Keck Observatory Archive (KOA). The frames live in
`data/Deimos-Feige_34/science/`.

> **Verified against the FITS headers on 2026-06-30.** An earlier draft of this
> file mis-stated the file count, the on-disk naming, and the observing modes;
> the tables and claims below reflect the actual headers.

## What this dataset is

**Feige 34** is a hot subdwarf (sdO) commonly used as a spectrophotometric
standard at northern observatories. Observations of it are typically used to
derive a sensitivity function for flux calibration of science data taken on
the same night.

Every file in this folder is a **science-mode exposure of Feige 34** — that
is, `KOAIMTYP = object` with the target being the standard star itself
(confirmed across all 38 files). None of these files are bias, dome flat, arc
lamp, or other instrument calibration frames in the conventional sense. They
are "calibration data" only in the flux-calibration sense (used to calibrate
other observations' flux scales).

## What this dataset is NOT

This is **not a self-contained reduction dataset**. There is no associated
science target on a galaxy field, cluster, or other multi-object configuration
to extract and reduce. Running the full pipeline against this collection
produces, at best, well-calibrated extracted spectra of Feige 34 — which is
useful for testing but not for demonstrating the SPIE paper's case study.

The dataset is also **heterogeneous across nights and configurations**: four
different programs, six observing dates, mixed gratings and filters, and a
mix of longslit and (on one night) MOS slit-mask exposures. A scientifically
valid reduction picks one night and one configuration; reducing the whole set
as a unit doesn't make sense.

## What this dataset IS good for

Three things, all useful in early development phases:

1. **Driving a real multi-extension / multi-amplifier loader.** DEIMOS frames
   are multi-extension: the primary HDU holds **no image data**, and the pixel
   data lives in per-amplifier extensions (`Video_Input_N`, 4096×2140 each).
   These files are the concrete real-instrument input that justifies a
   `CCDData`-based loader with amplifier assembly — a gap the synthetic
   single-HDU LRIS-2 flats hide (see "Compatibility with the current code"
   below).

2. **Validating the PypeIt path on real data.** `EdgeTraceSet` can in principle
   be run on the one night that has MOS masks (2003-01-10, the `LHEX01*`
   exposures). Important caveat: these are *object* exposures of a point source,
   not dome/twilight flats, so slit edges are not illuminated across the mask —
   tracing validation really wants the matching flat-field frames, which are
   **not** in this folder.

3. **Sanity-checking wavelength calibration.** Feige 34 has well-known
   spectral features (strong Balmer absorption, He lines). Once a wavelength
   solution is derived from an arc, comparing the extracted Feige 34 spectrum
   against published reference spectra is a quick correctness check.

For each of these, only a single file from the dataset is needed.

## File manifest

Files are named with the **original telescope convention**
`dMMDD_NNNN.fits` (e.g. `d1027_0120.fits`), where `MMDD` is the observation
date and `NNNN` the frame number. (The KOA `koaid` is recorded inside each
file's header, not in the filename.) Every row below was read from the headers:

| Date | Program | PI | Mode | N | Grating(s) | Filter(s) | HDUs |
|------|---------|-----|------|---|-----------|-----------|------|
| 2002-12-30 | ENG (DEIMOS Engineering) | KECK | Longslit | 3 | 600ZD / 1200G | GG455 / OG550 | 9 |
| 2003-01-10 | H37bD | Aussel (UH) | Longslit + MOS | 10 | 600ZD | GG400 | 15 |
| 2003-04-06 | C5D | Ellis (CIT) | Longslit (LongA) | 8 | 600ZD / 1200G | GG495 / OG550 | 15 |
| 2003-10-27 | U03D (DEEP2) | M. Davis (UCB) | Longslit | 5 | 600ZD / 1200G | BAL12 / GG455 / OG550 | 9 |
| 2003-10-28 | U03D (DEEP2) | M. Davis (UCB) | Longslit | 5 | 600ZD / 1200G | GG455 / OG550 | 9 |
| 2003-10-29 | U03D (DEEP2) | M. Davis (UCB) | Longslit | 7 | 600ZD / 1200G | BAL12 / GG455 / OG550 | 9 |

Notes:

- **The U03D / DEEP2 Feige 34 frames are longslit** (`SLMSKNAM = None`), not
  MOS. This is expected: the standard star is observed through a longslit, while
  the DEEP2 *science* targets use galaxy slit-masks (which are not in this
  folder). An earlier draft incorrectly labeled these as MOS.
- **Only the 2003-01-10 (H37bD) night contains MOS masks** — slit-mask names
  `LHEX01A/B/C` appear alongside `LongA` longslit frames there.
- HDU count varies by readout era: the 2003-01/04 nights have 15 extensions,
  the 2002-12 / 2003-10 nights have 9.

## What the DEEP2 subset could become, and how to complete it

The **U03D frames (rows for 2003-10-27/28/29) are from the DEEP2 Galaxy
Redshift Survey** — program `U03D`, PI Marc Davis (UC Berkeley), "The DEEP2
Survey of the Distant Universe." These are the flux-calibration standards from
three DEEP2 nights (5 + 5 + 7 = 17 frames here).

DEEP2 is a workhorse public DEIMOS survey with extensively documented
multi-slit observations of galaxy fields, full calibration coverage per night,
and published reductions (DEEP2 DR4) that can serve as ground truth. The
Feige 34 standards here are the natural flux calibrators for the science
exposures from the same nights.

**To complete a case-study dataset**: return to KOA and search Instrument =
DEIMOS, Program ID = `U03D`, UT dates 2003-10-27 to 2003-10-30 (the trailing
date catches biases taken post-UT-midnight), file types = any. That yields bias
frames, dome flats, arc lamps, slit-mask trace exposures, *and* the DEEP2
science exposures on real galaxy masks — plus these Feige 34 standards already
on disk for flux calibration.

The other Feige 34 nights (2002-12-30 ENG, 2003-01-10 H37bD, 2003-04-06 C5D)
are from unrelated programs and have no obvious upgrade path to a full case
study. They remain useful as auxiliary loading / sanity-check inputs.

## Compatibility with the current code

These frames **do not load through `core/io.load_flat_frame` as-is**, and that
is a useful finding:

- `load_flat_frame(path)` defaults to `hdu=0`, which here raises
  `ValueError: contains no image data` because the primary HDU is empty.
- `load_flat_frame(path, hdu=1)` succeeds but returns a **single amplifier**
  (4096×2140), not the assembled detector.
- The extensions are scaled integers (`BZERO`/`BSCALE`), which also trip
  Astropy's default memory-mapped read on direct `.data` access.

The takeaway: real Keck raw frames need a multi-extension, multi-amplifier
assembly step that the synthetic single-HDU LRIS-2 flats never exercised. When
that loader is built (the planned `CCDData` canonical data model — ADR not yet
written), DEIMOS frames should assemble into a single full-detector image, with
per-amplifier data retained for primitives that need it. PypeIt's `keck_deimos`
spectrograph already handles this assembly natively and is the reference:

```python
from pypeit.spectrographs.util import load_spectrograph
spec = load_spectrograph("keck_deimos")
```

## How to use this data during development

- **Phase 2 (tracing slice):** *not* a good fit — tracing wants illuminated
  flat-field slit edges, and these are point-source object exposures with no
  flats. The PypeIt development suite's `keck_deimos` calibration data is the
  correct input for tracing-primitive validation.
- **Phase 3 (Flow A) and Phase 4 (selective re-execution):** keep using the
  synthetic LRIS-2 flats; these DEIMOS frames are auxiliary only until a full
  DEEP2 night is downloaded.
- **Phase 7 (PyReduce primitives) / real-data loader:** the prime use. One or
  two of these frames make a good fixture for the multi-extension loader and for
  wavelength sanity checks against Feige 34's known features.

## Provenance and citation

If any reduction product derived from this data is used in the paper,
acknowledgments must include:

- **KOA:** "This research has made use of the Keck Observatory Archive (KOA),
  which is operated by the W. M. Keck Observatory and the NASA Exoplanet
  Science Institute (NExScI), under contract with the National Aeronautics
  and Space Administration."
- **Original PIs:** acknowledge the PIs whose programs contributed the data
  used in any published figure or measurement. For the DEEP2 files: Marc Davis
  (UC Berkeley), program U03D.
- **PypeIt DRP:** if PypeIt-reduced products from KOA are used, include the
  PypeIt citation (Prochaska et al. 2020).

Tracked separately in `docs/citations.md` (TODO).

## Storage and git

There is currently **no `.gitignore` and no `koaids.txt` manifest** in the data
tree, and the prototype is not yet under git. The intended policy, once it is:
commit only this document plus a `koaids.txt` manifest of the KOA ids, and keep
the ~4.9 GB of FITS out of version control (re-downloadable from KOA against the
id list). Until then the frames simply live untracked on disk.

## Cross-references

- `docs/lris-calibration.md` — the sibling **LRIS-Blue** Feige 34 dataset
  (`data/LRIS-Feige_34/`), same star, predecessor instrument, and (unlike this
  folder) with real bias/flat/arc calibration frames.
- `docs/data.md` — overall data strategy and dataset decisions.
- `docs/architecture.md` — the canonical internal data model (multi-extension
  FITS → `CCDData`) is planned, not yet written.
- `docs/plan.md` — current phase and how data fits into it.
