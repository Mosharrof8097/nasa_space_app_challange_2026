# Stage 1 — Duplicate Checking & Spatio-Temporal Clustering Report

**Generated:** 2026-10-07 19:08:18  
**Input:** `unified_global_fire_7d.csv` — 83,226 raw detections  
**Clustering mode:** GA-evolved per-biome radii  
**Temporal window:** same acquisition date AND same day/night overpass (~12.0 h)  
**Spatial grid:** cos(latitude)-corrected equal-ground-distance cells  
**Boundary handling:** Haversine union of adjacent cells within radius

---

## 1. Summary

| Metric | Value | Meaning |
| :--- | ---: | :--- |
| Raw detections | 83,226 | MODIS + VIIRS hotspots ingested |
| Exact duplicates | 0 (0.0%) | Identical coordinate, time and sensor |
| Sub-pixel detections merged | 48,356 | Extra pixels covering one physical fire |
| Physical fire events | 34,869 | Count after consolidation |
| Artificial inflation removed | 58.1% | Redundancy caused by sensor resolution disparity |
| VIIRS : MODIS raw ratio | 4.26:1 | Raw detection count ratio |
| Cross-sensor confirmed fires | 3,891 | Seen by BOTH satellites — our calibration ground truth |

---

## 2. Why this step is required

A MODIS pixel covers about 1 km x 1 km at nadir. A VIIRS pixel covers about
375 m x 375 m. One physical fire that MODIS records as a single detection can
therefore appear as several separate VIIRS detections. Counting raw detections
makes fire activity look like it jumped when VIIRS came online in 2012, even
though nothing changed on the ground.

This stage consolidates detections that fall inside one physical burn footprint
within one overpass window into a single fire event, so that later stages compare
fires rather than pixels.

### Energy accounting

When both satellites observe the same fire, adding their Fire Radiative Power
together would double-count the same emitted energy. This pipeline therefore
keeps `modis_frp_mw` and `viirs_frp_mw` as separate columns and exposes
`representative_frp_mw` for the non-double-counted value. Keeping the two sensors
separate is also what allows Stage 2 to calibrate them against each other on
genuinely paired observations.

---

## 3. Per-biome breakdown

| Biome | Radius | Raw | Fire events | Merged | Compression | Cross-sensor | Mean px/event |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Montane & Hills** | 1.20 km | 2,861 | 760 | 2,101 | 73.4% | 118 | 3.76 |
| **Dense Rainforest** | 0.80 km | 75,958 | 31,355 | 44,603 | 58.7% | 3,659 | 2.42 |
| **Agricultural Plains** | 1.50 km | 701 | 366 | 335 | 47.8% | 17 | 1.92 |
| **Savannas & Grasslands** | 1.50 km | 3,705 | 2,388 | 1,317 | 35.5% | 97 | 1.55 |

---

## 4. Output dataset

`deduplicated_data/harmonized_unique_fire_events_7d.csv`

| Column | Description |
| :--- | :--- |
| `fire_event_id` | Stable identifier for the consolidated physical fire |
| `acq_date`, `daynight` | Acquisition date and overpass window |
| `center_latitude`, `center_longitude` | Cluster centroid |
| `fire_class_id`, `biome_name` | Biome stratum |
| `pixel_detections_count` | Detections merged into this event |
| `total_frp_mw` | Raw sum of all detections (double-counts cross-sensor fires) |
| `representative_frp_mw` | Non-double-counted energy for the event |
| `modis_frp_mw`, `viirs_frp_mw` | Per-sensor energy, kept separate |
| `modis_pixels`, `viirs_pixels` | Per-sensor detection counts |
| `max_brightness_k` | Peak brightness temperature (MODIS band 21/22 or VIIRS I-4) |
| `sensor_type` | `MODIS`, `VIIRS` or `MODIS+VIIRS` |
| `cross_sensor_validated` | True when both satellites saw this fire |

---

## 5. Scope and limitations

- This run covers the **83,226-detection benchmark window** described above, not the full multi-year archive.
- Grid bucketing plus a Haversine adjacent-cell union is a close approximation of
  full ST-DBSCAN, chosen because it is near-linear and so scales to a multi-year
  global archive. Chains of fires longer than the neighbour search can in principle
  still be split.
- Biome labels currently come from the download region bounding box. Ingesting
  arbitrary global files will require a land-cover lookup to assign biomes.
