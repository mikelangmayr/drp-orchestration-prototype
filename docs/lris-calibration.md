# LRIS-Blue Calibration Frames

LRIS-Blue calibration frames (biases, dome flats, arc lamps) taken on nights
that also observed the spectrophotometric standard Feige 34, plus a few arcs
from other 2001 programs. Downloaded from the Keck Observatory Archive (KOA).
The frames live in `data/LRIS-Feige_34/calibration/` (24 files); the single
LRIS-Blue science frame is in `data/LRIS-Feige_34/science/`.

> **Verified against the FITS headers on 2026-06-30.** An earlier draft listed
> program IDs in the "Grating" columns; those are corrected to the real grism
> names below, and the loading notes now reflect the actual HDU structure.

## Folder note

These files were originally downloaded into `data/Deimos-Feige_34/calibration/`
alongside DEIMOS data. They were moved here because:

- The `lb` and `lblue` filename prefixes are LRIS-Blue naming conventions, not
  DEIMOS.
- Loading them uses PypeIt's `keck_lris_blue` spectrograph, not `keck_deimos`.
- The detector geometry and header conventions differ from DEIMOS.

Keep instrument-specific data in instrument-specific folders.

## What this dataset is

A mix of two kinds of LRIS-Blue data:

**One coherent calibration suite** from a single night (2002-01-07, Chris
Martin's program at CIT, program `C74L`, "Wide-Field Spectroscopic Survey of
m > 22.5 Emission-Line Galaxies toward the Rich Cluster Abell 851"). All twelve
frames share grism **600/4000** and slit **long_1.5**:

| File | Type | Exptime | Slit | Grism |
|------|------|---------|------|-------|
| lb0090 | flatlamp | 5s | long_1.5 | 600/4000 |
| lb0091 | flatlamp | 5s | long_1.5 | 600/4000 |
| lb0092 | flatlamp | 5s | long_1.5 | 600/4000 |
| lb0093 | arclamp | 1s | long_1.5 | 600/4000 |
| lb0094 | arclamp | 1s | long_1.5 | 600/4000 |
| lb0095–lb0101 | bias (×7) | 0s | long_1.5 | 600/4000 |

This is enough to build a master bias, a normalized master flat, and a
wavelength solution — a *real* calibration suite for one configuration on one
night.

**Scattered calibrations** from four other 2001 programs. The previous draft put
each program's *ID* in a "Grating" column; the real grisms are below:

| File | Date | Program | PI | Type | Slit / Mode | Grism |
|------|------|---------|-----|------|-------------|-------|
| lblue0018 | 2001-03-18 | C8L | Sargent (CIT) | arclamp | maskb1.sargent (MOS) | 300/5000 |
| lblue0211 | 2001-03-20 | C8L | Sargent (CIT) | arclamp | long_1.5 | 300/5000 |
| lblue1029 | 2001-04-21 | U37E | Perlmutter (UC-LBL) | flatlamp | long_1.0 | 300/5000 |
| lblue1029-2 | 2001-04-21 | U37E | Perlmutter (UC-LBL) | flatlamp | long_1.0 | 300/5000 |
| lblue1030 | 2001-04-21 | U37E | Perlmutter (UC-LBL) | flatlamp | long_1.0 | 300/5000 |
| lblue1031 | 2001-04-21 | U37E | Perlmutter (UC-LBL) | flatlamp | long_0.7 | 300/5000 |
| lblue1032 | 2001-04-21 | U37E | Perlmutter (UC-LBL) | flatlamp | long_0.7 | 300/5000 |
| lblue1033 | 2001-04-21 | U37E | Perlmutter (UC-LBL) | flatlamp | long_0.7 | 300/5000 |
| lblue0188 | 2001-11-15 | C57L | Steidel (CIT) | arclamp | long_1.0 | 300/5000 |
| lblue0189 | 2001-11-15 | C57L | Steidel (CIT) | arclamp | long_1.0 | 400/3400 |
| lblue0292 | 2001-11-16 | C57L | Steidel (CIT) | arclamp | long_1.0 | 300/5000 |
| lblue0293 | 2001-11-16 | C57L | Steidel (CIT) | arclamp | long_1.0 | 400/3400 |

These do not form a coherent calibration set: each program is represented only
by a few arc or flat frames, never enough to build a complete calibration for
that program's setup.

## Anomalies

**`lblue1033.fits` target is `s10039+0718`, not Feige 34** (confirmed in the
header). It was likely included in the download by mistake. If a different
target, it should be moved out of the Feige 34 folder or deleted.

**`lblue0018` is MOS, not longslit.** The `maskb1.sargent` slitmask name marks a
multi-object configuration (program "LRIS Spectra of Chandra/ACIS X-ray Sources
in the HDF"). This single arc isn't useful for case-study reduction by itself,
but it confirms LRIS MOS data from this era is on KOA — useful when planning a
multi-slit LRIS case study (see "Path forward").

## What this dataset is good for

The coherent 2002-01-07 suite is genuinely useful, and — importantly — it
**loads through the current code with no adapter work**:

1. **Loads directly via `core/io.load_flat_frame`.** Unlike DEIMOS (and unlike
   the 2011 LRIS science frame), these 2001–2002 LRIS-Blue frames are
   **single-HDU**: a 2048×2148 image in the primary HDU. `load_flat_frame(path)`
   returns them as-is — verified on a bias (`lb0095`, mean ≈ 1598) and a flat
   (`lb0090`, mean ≈ 1745). No multi-amplifier assembly needed.

2. **Real master-bias construction.** Seven biases is enough to median-combine a
   credible master bias — the natural first real input for the
   `make_master_bias` / `subtract_bias` primitives that are stubs today (Phase 3
   / ADR 0003), and for a PyReduce `Bias` primitive in Phase 7.

3. **Real flat normalization.** Three dome flats plus the master bias give a
   normalized master flat (PyReduce `Flat` / `NormalizeFlatField`).

4. **Real wavelength calibration.** Two arcs (grism 600/4000, slit long_1.5)
   give a real solution to test wavelength-calibration primitives against.

The scattered files are useful only as individual-frame loading tests or as
extra arcs for cross-validating wavelength solutions.

## What this dataset is NOT good for

Same caveat as the DEIMOS Feige 34 folder: **no science targets**. There is
nothing but Feige 34 to reduce and extract, so the science output is "extracted
spectrum of a standard star" — fine for validation, not compelling case-study
material.

Also **almost entirely longslit**. The paper's case study ideally shows
multi-slit reduction (LRIS-2's main mode); the only MOS frame here (`lblue0018`)
is a lone arc.

## Path forward for an LRIS case study

If LRIS is to be more than a loading/primitive-validation dataset:

- **Option A — complete the Martin Abell 851 program.** The 2002-01-07
  calibrations here pair with science exposures on the Abell 851 cluster on
  adjacent nights (e.g. 2002-01-08). Longslit, but a real galaxy-cluster
  reduction with a matchable reference.
- **Option B — pull a Steidel z~3 MOS night.** Program `C57L` (2001-11-15/16) is
  a multi-object Lyman-break-galaxy survey. Pull full nights with science
  exposures and matching calibrations. Multi-slit, scientifically rich, heavily
  cited — the most reference reductions to compare against.
- **Option C — pull a Sargent HDF MOS night.** Program `C8L` (2001-03-18),
  multi-object spectroscopy of X-ray sources in the Hubble Deep Field. Same
  shape as Option B, more niche.

If the paper's center of gravity is LRIS-2, a multi-slit LRIS case study
(Option B or C) is more on-message than the DEIMOS/DEEP2 path. Worth deciding
before pulling another batch.

## Loading these files

LRIS-Blue raw data uses PypeIt's `keck_lris_blue` spectrograph:

```python
from pypeit.spectrographs.util import load_spectrograph
spec = load_spectrograph("keck_lris_blue")
```

Important: PypeIt has separate configs for `keck_lris_blue`, `keck_lris_red`,
and `keck_lris_red_mark4`. Do not mix them; `lb*` / `lblue*` files require
`keck_lris_blue`.

Note the HDU heterogeneity across LRIS eras: the **2001–2002 frames here are
single-HDU** (data in the primary, loads directly), whereas the **2011 science
frame** in `science/` is multi-extension (empty primary; per-amplifier `VidInp`
extensions, like DEIMOS). A general LRIS adapter must handle both; the planned
`CCDData` data model is where that assembly lives (ADR not yet written).

## How to use this data during development

- **Now (Phase 3/4 → real master bias):** the seven 2002-01-07 biases are the
  first real input that can replace the stub master bias behind the Flow A
  calibration arm — they load with zero adapter work.
- **Phase 7 (polyglot primitives):** the 12-file 2002-01-07 suite is the natural
  test bed for PyReduce `Bias`, `Flat`, `NormalizeFlatField`, and wavelength
  steps, since they map cleanly onto these inputs.

## Provenance and citation

If any reduction product derived from this data appears in the paper:

- **KOA** — standard KOA acknowledgment (see `docs/deimos-feige34.md`).
- **Original PIs** — for the Martin Abell 851 calibrations, Chris Martin
  (Caltech), program `C74L`; other PIs as appropriate per frame.

Tracked separately in `docs/citations.md` (TODO).

## Storage and git

`data/LRIS-Feige_34/koaids.txt` is the KOA-id manifest for this dataset, and
`data/.gitignore` excludes the FITS pixels from version control (re-downloadable
from KOA against the manifest). Commit the manifest and this document, not the
frames.

## Cross-references

- `docs/deimos-feige34.md` — sibling DEIMOS dataset, same star, different
  instrument.
- `docs/data.md` — overall data strategy and dataset decisions.
- `docs/architecture.md` — the canonical internal data model (multi-extension
  FITS → `CCDData`) is planned, not yet written.
- `docs/plan.md` — current phase and how data fits into it.
