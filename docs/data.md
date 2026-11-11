# Data strategy

What test data the prototype uses, why, and how it maps onto the phases and the
paper's claims. Per-dataset detail lives in the dataset docs; this file is the
overview and the decisions.

## Principle: real frames over synthetic

Synthetic spectra are a stopgap. Real KOA frames carry real stars, real read
noise, cosmic rays, bad columns, true multi-amplifier geometry, and real
slit-mask edges — exactly the things a DRP must survive. Since LRIS-2 has no
on-sky data yet, **LRIS-1 and DEIMOS are the proxies** (the same `keck_lris_*` /
`keck_deimos` PypeIt configs the algorithm layer targets). Synthetic frames are
kept only where no real equivalent is wired in yet.

## Datasets on disk

All live under the repository-sibling `data/` tree. FITS pixels are git-ignored
(`data/.gitignore`); each dataset carries a `koaids.txt` manifest so it is
re-downloadable from KOA.

| Dataset | Path | Contents | Role |
|---------|------|----------|------|
| Synthetic LRIS-2 | `lris2-drp/data/lris2_flats`, `…/lris2_arcs` | ray-traced flats + arcs (4080², single-HDU) | Current Flow A / tracing input; stopgap |
| LRIS 2002-01-07 night | `data/LRIS-2002-01-07/` | **104 cal + 61 sci** (Blue+Red, gzipped, single-HDU) | **Primary case study** (see below) |
| DEIMOS 2003-10-27 night | `data/Deimos-2003-10-27/` | **67 cal + 59 sci** (gzipped, 16-HDU multi-amp) | DEEP2-style case-study candidate; ground-truth cross-check |
| LRIS Feige 34 cals | `data/LRIS-Feige_34/calibration` | 24 LRIS-Blue bias/flat/arc frames | Real bias/flat/wavecal primitive fixtures |
| LRIS Feige 34 sci | `data/LRIS-Feige_34/science` | 1 LRIS-Blue 2011 frame (multi-ext) | Multi-extension loader fixture |
| DEIMOS Feige 34 | `data/Deimos-Feige_34/science` | 38 DEIMOS standard-star frames (multi-amp) | Multi-amp loader + wavecal sanity |

Dataset docs: `docs/lris-calibration.md`, `docs/deimos-feige34.md`. (The synthetic
set predates these docs and is described in the root project notes.)

## The case study: 2002-01-07 LRIS night

This is the prototype's real end-to-end reduction target. One night of the
Martin program (`C74L`) on two galaxy clusters — **Abell 851** and **CL0024** —
with both LRIS channels:

- **Science:** real MOS spectroscopy on masks `a851b/d/f.martin`,
  `c0024a/b.martin` (targets `A851-B/D/F`, `CL0024-A/b`), plus 4 `Feige 34` flux
  standards and direct-imaging acquisitions.
- **Calibration, same night:** 40 bias, 20 dome flat, 19 arc (plus focus /
  acquisition frames that are not reduction inputs).
- Grisms: Blue `600/4000`, Red `600/5000`.

Why this one: it is the only on-disk dataset that is simultaneously *real*,
*multi-slit* (LRIS-2's main mode), *self-contained* (science + matching cals +
flux standard on one night), and *dual-channel*. It exercises every abstract
claim on real data, and the DEEP2-style published context for these clusters
gives a comparison reference.

### Configuration grouping

The night is heterogeneous, so a valid reduction groups frames by **unique
instrument configuration** — `(channel, mask, grism)` — and reduces each group
independently. For example *A851-B / Blue / 600/4000* = its science exposures +
the `a851b` dome flat + `a851b` arcs + the shared biases + a Feige 34 standard.
This is the same "group by configuration" the production DRP is built around, and
it is the natural unit for the parallelism (independent groups) and
selective-re-execution (re-run one group) demonstrations.

### The DEIMOS 2003-10-27 alternative

A second real multi-slit night is on disk: a DEEP2-style DEIMOS night
(`data/Deimos-2003-10-27/`, KOA cart 1382) with **~10 real MOS science masks**
(`goodsS` = GOODS-South, `MS0451_Mask14/15`, and DEEP2 fields `3108.W`,
`3110.W`, `3111.W`, `3342.E`, `4101.W`, `4104.W`), matching per-mask dome flats
(30) + arcs (10) + biases (11), and 5 Feige 34 longslit standards. Gratings
1200G / 600ZD.

It is richer than the LRIS night (more masks, famous fields) and DEEP2 DR4 is a
**published reduction** to validate outputs against. Two costs make it the
*secondary* dataset rather than the primary case study:

- **Format.** DEIMOS frames are 16-HDU multi-amp (8 chips × 2 amps, empty
  primary) — they need the multi-amp mosaic loader before anything runs, whereas
  the LRIS night loads today.
- **On-message.** LRIS is the direct LRIS-2 proxy; DEIMOS is a different
  instrument. The paper's center of gravity is LRIS-2.

Recommended role: **LRIS 2002-01-07 is the primary case study; DEIMOS 2003-10-27
is the ground-truth cross-check** and the second instrument that proves the
primitive-source-agnostic / multi-format claim once the multi-amp loader exists.
(Final call is open — see `docs/plan.md` open questions.)

## Real-data findings (and the gaps they expose)

Validating against these frames surfaced concrete gaps that synthetic single-HDU
flats hid:

1. **HDU heterogeneity.** The 2001–2002 LRIS frames are single-HDU
   (2048×2148, data in the primary) and load directly via
   `core.io.load_flat_frame`. The 2011 LRIS frame and all DEIMOS frames are
   multi-extension with an empty primary and per-amplifier extensions, and do
   **not** load via `hdu=0`. A real loader must assemble amplifiers into one
   detector image (the planned `CCDData` data model).

2. **Raw frames need orientation/preprocessing before tracing.** Feeding a raw
   LRIS MOS dome flat straight to the tracing primitive found **0 slits** — the
   slits run along the wrong axis and the frame still carries overscan and no
   bias subtraction. Transposing to PypeIt's `(nspec, nspatial)` convention
   recovered real slit detections (4 of the brightest slits). Full quality needs
   overscan/trim/bias as well. The synthetic flats were already in science
   orientation, hiding this. → motivates a **raw-image preprocessing primitive**
   (overscan, trim, orient, amp-mosaic) ahead of tracing; see `docs/plan.md`.

3. **Discovery must handle gzipped, nested KOA carts.** KOA delivers
   `*.fits.gz` several directories deep (`KOA_29596/LRIS/raw/cal`).
   `discover_fits` now matches `.gz` and takes `recursive=True`.

## Conventions

- One `koaids.txt` per dataset root maps each on-disk file to its KOA id;
  re-downloading those ids reproduces the dataset exactly.
- `data/.gitignore` excludes `*.fits`, `*.fits.gz`, preview `*.jpg`, and
  `.DS_Store`; manifests are tracked.
- Keep instrument-specific data in instrument-specific folders (LRIS vs DEIMOS
  need different PypeIt spectrographs and have different formats).

## Provenance

Any reduction product used in the paper must carry the KOA acknowledgment and
the relevant original-PI credit; see the per-dataset docs. Citation tracking:
`docs/citations.md` (TODO).
