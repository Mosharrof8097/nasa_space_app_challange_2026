#!/usr/bin/env python3
"""
EmberSync — Stage 1: Duplicate Checking & Spatio-Temporal Clustering
NASA Space Apps Challenge 2026: Harmonization of MODIS and VIIRS Hot Spots

Pipeline position
-----------------
    raw FIRMS detections
            |
            v
    [THIS SCRIPT] exact-duplicate removal + spatio-temporal clustering
            |
            v
    Stage 2: genetic algorithm calibration  (run_genetic_algorithm_mapping.py)
            |
            v  (feeds the evolved per-biome radius back into this script)
    [THIS SCRIPT --use-ga-radii] final consolidated dataset

Run order
---------
    python3 run_deduplication_and_clustering.py              # bootstrap, 1.0 km default
    python3 ../genetic_algorithm_harmonization/run_genetic_algorithm_mapping.py
    python3 run_deduplication_and_clustering.py --use-ga-radii   # closes the loop

The second clustering pass is what makes the genetic algorithm's discovered radius
actually matter. In the first version of this pipeline the GA reported an "optimal
clustering radius" per biome that was never applied to the clustering step, so the
two stages were disconnected.

The clustering mathematics live in clustering_core.py; see that module's docstring
for the scientific rationale behind each correction.
"""

import argparse
import json
import os
from datetime import datetime

import pandas as pd

from clustering_core import assign_clusters, aggregate_events

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DEDUPLICATED_DIR = os.path.join(OUTPUT_DIR, "deduplicated_data")
RAW_DATA_PATH = os.path.join(
    BASE_DIR, "data download", "raw_data", "unified_global_fire_7d.csv"
)
GA_REPORT_PATH = os.path.join(
    BASE_DIR, "genetic_algorithm_harmonization", "ga_optimization_report.json"
)

os.makedirs(DEDUPLICATED_DIR, exist_ok=True)

# Bootstrap radius, used on the first pass before the GA has evolved anything.
# 1.0 km matches the nominal MODIS pixel scale at nadir.
DEFAULT_RADIUS_KM = 1.0

# The day and night overpass windows are each ~12 h, so grouping by
# (acquisition date, day/night flag) applies this window literally.
TEMPORAL_WINDOW_HOURS = 12.0

BIOMES = [
    (1, "Montane & Hills"),
    (2, "Dense Rainforest"),
    (3, "Agricultural Plains"),
    (4, "Savannas & Grasslands"),
]


def load_ga_radii():
    """Read the per-biome radius evolved by Stage 2, if Stage 2 has already run."""
    if not os.path.exists(GA_REPORT_PATH):
        print(f"[!] No GA report at {GA_REPORT_PATH} — falling back to default radius.")
        return None
    with open(GA_REPORT_PATH) as f:
        report = json.load(f)
    radii = {}
    for name, entry in report.items():
        r = entry.get("optimal_chromosome", {}).get("optimal_clustering_radius_km")
        if r:
            radii[name] = float(r)
    if not radii:
        print("[!] GA report present but contains no radii — using default radius.")
        return None
    print("[✓] Loaded GA-evolved clustering radii:")
    for n, r in radii.items():
        print(f"      {n:<24} {r:.2f} km")
    return radii


def run(use_ga_radii: bool):
    print("=" * 80)
    print("EMBERSYNC STAGE 1 — DUPLICATE CHECKING & SPATIO-TEMPORAL CLUSTERING")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if not os.path.exists(RAW_DATA_PATH):
        print(f"[!] Raw data not found at {RAW_DATA_PATH}")
        return

    ga_radii = load_ga_radii() if use_ga_radii else None
    mode = "GA-evolved per-biome radii" if ga_radii else f"default {DEFAULT_RADIUS_KM} km radius"
    print(f"[*] Clustering mode: {mode}\n")

    print(f"[*] Loading {RAW_DATA_PATH}")
    df = pd.read_csv(RAW_DATA_PATH, low_memory=False)
    total_raw = len(df)
    print(f"[✓] Loaded {total_raw:,} raw active-fire detections.")

    # --- Sanitation
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["frp"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0)
    if "daynight" not in df.columns:
        df["daynight"] = "D"
    df = df.dropna(subset=["latitude", "longitude", "acq_date"]).copy()

    report = {
        "analysis_timestamp": datetime.now().isoformat(),
        "input_file": RAW_DATA_PATH,
        "total_raw_records": total_raw,
        "valid_sanitized_records": len(df),
        "parameters": {
            "clustering_mode": mode,
            "default_radius_km": DEFAULT_RADIUS_KM,
            "per_biome_radius_km": ga_radii or {n: DEFAULT_RADIUS_KM for _, n in BIOMES},
            "temporal_window_hours": TEMPORAL_WINDOW_HOURS,
            "temporal_grouping": "same acquisition date AND same day/night overpass",
            "grid": "cos(latitude)-corrected equal-ground-distance cells",
            "boundary_handling": "Haversine union of adjacent cells within radius",
            "energy_accounting": "per-sensor FRP kept separate; representative_frp_mw avoids double counting",
        },
        "exact_duplicates": {},
        "spatio_temporal_clusters": {},
        "class_breakdown": {},
        "sensor_breakdown": {},
    }

    # --- Step 1: exact duplicates
    print("\n>>> [Step 1] Exact duplicate detection (same lat, lon, date, time, sensor)")
    exact_subset = ["latitude", "longitude", "acq_date", "acq_time", "source_sensor"]
    dup_mask = df.duplicated(subset=exact_subset, keep="first")
    exact_dup_count = int(dup_mask.sum())
    print(f"    Exact duplicates: {exact_dup_count:,} ({exact_dup_count / total_raw * 100:.2f}%)")
    report["exact_duplicates"] = {
        "count": exact_dup_count,
        "percentage": round(exact_dup_count / total_raw * 100, 3),
    }
    df = df[~dup_mask].copy()

    # --- Step 2: spatio-temporal clustering, per biome
    print("\n>>> [Step 2] Spatio-temporal clustering (per biome)")
    event_frames = []
    class_stats = {}
    total_redundant = 0
    id_offset = 0

    for class_id, class_name in BIOMES:
        sub = df[df["fire_class_id"] == class_id].copy()
        if sub.empty:
            continue

        radius = (ga_radii or {}).get(class_name, DEFAULT_RADIUS_KM)
        print(f"\n    Class {class_id} — {class_name}  ({len(sub):,} detections, R = {radius:.2f} km)")

        labels = assign_clusters(sub, radius)
        events = aggregate_events(sub, labels, class_id, class_name, id_offset=id_offset)
        id_offset += len(events)

        redundant = len(sub) - len(events)
        total_redundant += redundant
        event_frames.append(events)

        cross = int(events["cross_sensor_validated"].sum())
        class_stats[class_name] = {
            "class_id": class_id,
            "clustering_radius_km": radius,
            "raw_records": int(len(sub)),
            "consolidated_fire_events": int(len(events)),
            "multi_pixel_redundancy_count": int(redundant),
            "compression_ratio": f"{redundant / len(sub) * 100:.1f}%",
            "cross_sensor_agreements": cross,
            "mean_pixels_per_event": round(float(events["pixel_detections_count"].mean()), 2),
            "max_pixels_per_event": int(events["pixel_detections_count"].max()),
        }
        print(f"      -> {len(events):,} physical fire events")
        print(f"      -> {redundant:,} sub-pixel detections merged ({redundant / len(sub) * 100:.1f}%)")
        print(f"      -> {cross:,} fires confirmed by BOTH satellites (calibration ground truth)")

    consolidated = pd.concat(event_frames, ignore_index=True)

    report["class_breakdown"] = class_stats
    report["spatio_temporal_clusters"] = {
        "total_unique_physical_fires": int(len(consolidated)),
        "total_multi_pixel_sub_detections": int(total_redundant),
        "overall_clustering_reduction_percentage": round(total_redundant / len(df) * 100, 2),
    }

    sensor_counts = df["source_sensor"].value_counts().to_dict()
    report["sensor_breakdown"] = {
        "raw_counts": {str(k): int(v) for k, v in sensor_counts.items()},
        "viirs_to_modis_raw_ratio": round(
            sensor_counts.get("VIIRS", 0) / max(sensor_counts.get("MODIS", 1), 1), 2
        ),
        "clustered_cross_sensor_matches": int(consolidated["cross_sensor_validated"].sum()),
        "mean_viirs_pixels_per_cross_sensor_fire": round(
            float(
                consolidated.loc[consolidated["cross_sensor_validated"], "viirs_pixels"].mean()
            ),
            2,
        )
        if consolidated["cross_sensor_validated"].any()
        else None,
        "mean_modis_pixels_per_cross_sensor_fire": round(
            float(
                consolidated.loc[consolidated["cross_sensor_validated"], "modis_pixels"].mean()
            ),
            2,
        )
        if consolidated["cross_sensor_validated"].any()
        else None,
    }

    out_csv = os.path.join(DEDUPLICATED_DIR, "harmonized_unique_fire_events_7d.csv")
    consolidated.to_csv(out_csv, index=False)
    print(f"\n[✓] Consolidated dataset -> {out_csv}")
    print(f"    {len(consolidated):,} physical fire events, {len(consolidated.columns)} columns")

    json_path = os.path.join(OUTPUT_DIR, "duplicate_checking_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[✓] JSON report      -> {json_path}")

    write_markdown_report(report, OUTPUT_DIR)

    print("\n" + "=" * 80)
    print("STAGE 1 COMPLETE")
    print("=" * 80)
    return report


def write_markdown_report(report, out_dir):
    md_path = os.path.join(out_dir, "DUPLICATE_CHECKING_AND_CLUSTERING_REPORT.md")
    st = report["spatio_temporal_clusters"]
    sb = report["sensor_breakdown"]
    params = report["parameters"]

    lines = [
        "# Stage 1 — Duplicate Checking & Spatio-Temporal Clustering Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Input:** `{os.path.basename(report['input_file'])}` — {report['total_raw_records']:,} raw detections  ",
        f"**Clustering mode:** {params['clustering_mode']}  ",
        f"**Temporal window:** {params['temporal_grouping']} (~{params['temporal_window_hours']} h)  ",
        f"**Spatial grid:** {params['grid']}  ",
        f"**Boundary handling:** {params['boundary_handling']}",
        "",
        "---",
        "",
        "## 1. Summary",
        "",
        "| Metric | Value | Meaning |",
        "| :--- | ---: | :--- |",
        f"| Raw detections | {report['total_raw_records']:,} | MODIS + VIIRS hotspots ingested |",
        f"| Exact duplicates | {report['exact_duplicates']['count']:,} ({report['exact_duplicates']['percentage']}%) | Identical coordinate, time and sensor |",
        f"| Sub-pixel detections merged | {st['total_multi_pixel_sub_detections']:,} | Extra pixels covering one physical fire |",
        f"| Physical fire events | {st['total_unique_physical_fires']:,} | Count after consolidation |",
        f"| Artificial inflation removed | {st['overall_clustering_reduction_percentage']}% | Redundancy caused by sensor resolution disparity |",
        f"| VIIRS : MODIS raw ratio | {sb['viirs_to_modis_raw_ratio']}:1 | Raw detection count ratio |",
        f"| Cross-sensor confirmed fires | {sb['clustered_cross_sensor_matches']:,} | Seen by BOTH satellites — our calibration ground truth |",
        "",
        "---",
        "",
        "## 2. Why this step is required",
        "",
        "A MODIS pixel covers about 1 km x 1 km at nadir. A VIIRS pixel covers about",
        "375 m x 375 m. One physical fire that MODIS records as a single detection can",
        "therefore appear as several separate VIIRS detections. Counting raw detections",
        "makes fire activity look like it jumped when VIIRS came online in 2012, even",
        "though nothing changed on the ground.",
        "",
        "This stage consolidates detections that fall inside one physical burn footprint",
        "within one overpass window into a single fire event, so that later stages compare",
        "fires rather than pixels.",
        "",
        "### Energy accounting",
        "",
        "When both satellites observe the same fire, adding their Fire Radiative Power",
        "together would double-count the same emitted energy. This pipeline therefore",
        "keeps `modis_frp_mw` and `viirs_frp_mw` as separate columns and exposes",
        "`representative_frp_mw` for the non-double-counted value. Keeping the two sensors",
        "separate is also what allows Stage 2 to calibrate them against each other on",
        "genuinely paired observations.",
        "",
        "---",
        "",
        "## 3. Per-biome breakdown",
        "",
        "| Biome | Radius | Raw | Fire events | Merged | Compression | Cross-sensor | Mean px/event |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for name, s in report["class_breakdown"].items():
        lines.append(
            f"| **{name}** | {s['clustering_radius_km']:.2f} km | {s['raw_records']:,} | "
            f"{s['consolidated_fire_events']:,} | {s['multi_pixel_redundancy_count']:,} | "
            f"{s['compression_ratio']} | {s['cross_sensor_agreements']:,} | {s['mean_pixels_per_event']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Output dataset",
        "",
        "`deduplicated_data/harmonized_unique_fire_events_7d.csv`",
        "",
        "| Column | Description |",
        "| :--- | :--- |",
        "| `fire_event_id` | Stable identifier for the consolidated physical fire |",
        "| `acq_date`, `daynight` | Acquisition date and overpass window |",
        "| `center_latitude`, `center_longitude` | Cluster centroid |",
        "| `fire_class_id`, `biome_name` | Biome stratum |",
        "| `pixel_detections_count` | Detections merged into this event |",
        "| `total_frp_mw` | Raw sum of all detections (double-counts cross-sensor fires) |",
        "| `representative_frp_mw` | Non-double-counted energy for the event |",
        "| `modis_frp_mw`, `viirs_frp_mw` | Per-sensor energy, kept separate |",
        "| `modis_pixels`, `viirs_pixels` | Per-sensor detection counts |",
        "| `max_brightness_k` | Peak brightness temperature (MODIS band 21/22 or VIIRS I-4) |",
        "| `sensor_type` | `MODIS`, `VIIRS` or `MODIS+VIIRS` |",
        "| `cross_sensor_validated` | True when both satellites saw this fire |",
        "",
        "---",
        "",
        "## 5. Scope and limitations",
        "",
        f"- This run covers the **{report['total_raw_records']:,}-detection benchmark window** described above, not the full multi-year archive.",
        "- Grid bucketing plus a Haversine adjacent-cell union is a close approximation of",
        "  full ST-DBSCAN, chosen because it is near-linear and so scales to a multi-year",
        "  global archive. Chains of fires longer than the neighbour search can in principle",
        "  still be split.",
        "- Biome labels currently come from the download region bounding box. Ingesting",
        "  arbitrary global files will require a land-cover lookup to assign biomes.",
    ]

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[✓] Markdown report  -> {md_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="EmberSync Stage 1 clustering")
    ap.add_argument(
        "--use-ga-radii",
        action="store_true",
        help="Cluster with the per-biome radii evolved by Stage 2 (run Stage 2 first)",
    )
    args = ap.parse_args()
    run(use_ga_radii=args.use_ga_radii)
