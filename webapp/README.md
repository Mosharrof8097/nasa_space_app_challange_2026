# EmberSync Dashboard (Team ASL NOVA, NASA Space Apps 2026)

Static single-page dashboard. No build step, no npm. Leaflet and Chart.js load from cdnjs, map tiles from OpenStreetMap (internet needed).

## Run
    cd webapp && python3 -m http.server 8000     # then open http://localhost:8000

Double-clicking `index.html` also works, but browsers block `fetch()` on `file://`. For that case run `python3 make_offline_data.py` once (re-run whenever the JSON changes); it writes `data/dashboard_data.js`, used as a fallback.

## Data
Everything is read from `data/dashboard_data.json`. Missing fields render as "—" or "pending". If `meta.note` contains "PLACEHOLDER", a banner is shown. The 2000-2026 timeline is labelled "Modeled baseline projection" unless `raw_vs_harmonized.is_modeled` is explicitly `false`.

## Sections
- Header: wordmark, tagline, challenge/team, "Data scope" badge.
- KPI row: raw detections, fire events, inflation removed, cross-sensor matches, plus MODIS/VIIRS split bar.
- Before vs after: keyboard-operable Raw/Harmonized radios and a scrub slider morph one line from amber (raw, 2012 cliff) to cyan (harmonized). Series are indexed to their own 2000-2011 mean so different units share an axis; the 2011-to-2012 readout is computed from the data.
- Map: Leaflet, biome checkboxes, raw/harmonized FRP sizing, thinning above 2,500 visible points, popups, white ring = both satellites.
- Calendar: windows of 31 days or fewer render as one row of large day cells; longer ranges become a GitHub-style week grid (365 days supported). Critical = solid red outline + "!!"/diamond; Elevated = dashed yellow outline + triangle. Biome tabs, hover/focus tooltip.
- Biome table: radius, exponent, energy fit, R2/MAE, cross-sensor, inflation (cards on phones).
- GA convergence: best fitness per biome, optional population average.
- Footer: team roster (edit the `#team` list in `index.html`) and the three citations.
