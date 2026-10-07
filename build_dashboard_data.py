#!/usr/bin/env python3
"""
EmberSync — Dashboard data builder

Collapses the outputs of Stage 1 (clustering), Stage 2 (GA calibration) and Stage 3
(burning calendar) into the single JSON file the web dashboard reads.

Run after the pipeline:
    python3 duplicate_checking_and_clustering/run_deduplication_and_clustering.py
    python3 genetic_algorithm_harmonization/run_genetic_algorithm_mapping.py
    python3 duplicate_checking_and_clustering/run_deduplication_and_clustering.py --use-ga-radii
    python3 genetic_algorithm_harmonization/run_genetic_algorithm_mapping.py --apply-only
    python3 build_dashboard_data.py

Every figure written here is derived from the files above. Nothing is hardcoded, so the
dashboard cannot drift away from what the pipeline actually produced.
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CLUSTER_REPORT = os.path.join(BASE, "duplicate_checking_and_clustering", "duplicate_checking_report.json")
GA_REPORT = os.path.join(BASE, "genetic_algorithm_harmonization", "ga_optimization_report.json")
HARMONIZED_CSV = os.path.join(BASE, "genetic_algorithm_harmonization", "ga_optimized_harmonized_dataset.csv")
HISTORICAL_CSV = os.path.join(BASE, "historical_harmonized_time_series_2000_2026", "historical_26yr_burning_calendar_matrix.csv")
OUT_JSON = os.path.join(BASE, "webapp", "data", "dashboard_data.json")

# Map points are sampled so the browser stays responsive. Cross-sensor-validated and
# high-energy fires are always kept; the remainder is sampled reproducibly.
MAX_MAP_POINTS = 6000
REGIONS = {
    "Montane & Hills": "Western USA / Sierra Nevada",
    "Dense Rainforest": "Amazon Basin, Brazil",
    "Agricultural Plains": "South Asia / Indo-Gangetic Plain",
    "Savannas & Grasslands": "Southern & Central Africa",
}


def build_biomes(cluster_report, ga_report, coverage):
    out = []
    for name, cs in cluster_report["class_breakdown"].items():
        ga = ga_report.get(name, {})
        chrom = ga.get("optimal_chromosome", {})
        hold = ga.get("validation", {}).get("holdout", {})
        dist = hold.get("distribution", {})
        perfire = hold.get("per_fire_skill", {})

        out.append({
            "class_id": cs["class_id"],
            "name": name,
            "region": REGIONS.get(name, ""),
            "raw_records": cs["raw_records"],
            "fire_events": cs["consolidated_fire_events"],
            "inflation_removed_pct": round(
                cs["multi_pixel_redundancy_count"] / cs["raw_records"] * 100, 2
            ),
            "cross_sensor_matches": cs["cross_sensor_agreements"],
            "mean_pixels_per_event": cs["mean_pixels_per_event"],
            "days_covered": coverage.get(name, 0),
            "optimal_radius_km": chrom.get("optimal_clustering_radius_km"),
            "calibration": {
                "w_frp": chrom.get("w_frp_scaling"),
                "power_exponent": chrom.get("power_exponent"),
                "w_brightness": chrom.get("w_brightness"),
                "cluster_scale": chrom.get("cluster_scale"),
            },
            "fit": {
                "distribution_fit_pct": dist.get("distribution_fit_pct"),
                "median_ratio_before": dist.get("median_ratio_before"),
                "median_ratio_after": dist.get("median_ratio_after"),
                "n_validation_pairs": hold.get("n_pairs"),
                "validation_split": ga.get("validation", {}).get("split"),
                "per_fire_r_log10": perfire.get("pearson_r_log10"),
                "per_fire_r2": perfire.get("r2"),
                "per_fire_median_rel_error_pct": perfire.get("median_rel_error_pct"),
            },
            "viirs_to_modis_event_ratio": ga.get("objectives", {}).get(
                "viirs_to_modis_event_count_ratio"
            ),
            "ga_convergence": ga.get("convergence_history", []),
            "radius_sweep": ga.get("radius_sweep", []),
        })
    out.sort(key=lambda b: b["class_id"])
    return out


def build_calendar(df):
    """Daily burning activity per biome, with a Z-score against the ingested window."""
    g = (
        df.groupby(["acq_date", "fire_class_id", "biome_name"], as_index=False)
        .agg(
            events=("fire_event_id", "size"),
            frp=("representative_frp_mw", "sum"),
            harmonized_frp=("harmonized_frp_mw", "sum"),
            cross_sensor=("cross_sensor_validated", "sum"),
        )
    )

    rows = []
    for _, sub in g.groupby("fire_class_id"):
        mean = sub["harmonized_frp"].mean()
        std = sub["harmonized_frp"].std(ddof=0)
        for _, r in sub.iterrows():
            z = float((r["harmonized_frp"] - mean) / std) if std and std > 0 else 0.0
            if z >= 2.0:
                status = "CRITICAL_ANOMALY"
            elif z >= 1.0:
                status = "ELEVATED_RISK"
            else:
                status = "NORMAL"
            rows.append({
                "date": str(r["acq_date"]),
                "class_id": int(r["fire_class_id"]),
                "events": int(r["events"]),
                "frp": round(float(r["frp"]), 1),
                "harmonized_frp": round(float(r["harmonized_frp"]), 1),
                "cross_sensor": int(r["cross_sensor"]),
                "z_score": round(z, 2),
                "status": status,
            })
    rows.sort(key=lambda r: (r["date"], r["class_id"]))
    return rows


def build_map_points(df):
    keep = df["cross_sensor_validated"].to_numpy(dtype=bool)
    budget = MAX_MAP_POINTS - int(keep.sum())
    if budget > 0:
        rest = df.loc[~keep]
        if len(rest) > budget:
            # Keep the strongest fires, then a reproducible random sample of the rest,
            # so dense regions stay representative instead of being truncated.
            strong_n = budget // 2
            strong_idx = rest["harmonized_frp_mw"].nlargest(strong_n).index
            remainder = rest.drop(index=strong_idx)
            rand_idx = remainder.sample(
                n=min(budget - strong_n, len(remainder)), random_state=42
            ).index
            chosen = df.index[keep].union(strong_idx).union(rand_idx)
        else:
            chosen = df.index
    else:
        chosen = df.index[keep]

    sel = df.loc[chosen]
    return [
        {
            "lat": round(float(r.center_latitude), 4),
            "lon": round(float(r.center_longitude), 4),
            "frp": round(float(r.representative_frp_mw), 2),
            "harmonized_frp": round(float(r.harmonized_frp_mw), 2),
            "class_id": int(r.fire_class_id),
            "sensor": str(r.sensor_type),
            "date": str(r.acq_date),
            "pixels": int(r.pixel_detections_count),
            "cross_sensor": bool(r.cross_sensor_validated),
        }
        for r in sel.itertuples()
    ], len(sel)


def build_long_timeline(measured_inflation_factor):
    """
    The 2000-2026 raw-vs-harmonized exhibit.

    IMPORTANT: the long time series is a MODELLED baseline. The multi-year FIRMS archive
    has not been ingested yet, so these yearly values come from
    historical_26yr_burning_calendar_matrix.csv, which is generated from biome seasonal
    cycles and documented megafire years — not from measured detections. The dashboard
    labels it as such, and `is_modeled` is set to true so the page cannot present it as
    measured data.

    Both series are expressed in the SAME unit (fire events per year) so they share one
    axis honestly:
      raw         = MODIS detections + VIIRS detections
      harmonized  = MODIS detections + VIIRS detections / f
    where f is the per-fire count inflation factor MEASURED from our paired fires
    (mean VIIRS detections per confirmed fire / mean MODIS detections per confirmed fire).
    """
    if not os.path.exists(HISTORICAL_CSV):
        return None

    h = pd.read_csv(HISTORICAL_CSV)
    yearly = h.groupby("year", as_index=False).agg(
        modis=("modis_count", "sum"), viirs=("viirs_count", "sum")
    )
    raw = (yearly["modis"] + yearly["viirs"]).round(0)
    harmonized = (yearly["modis"] + yearly["viirs"] / measured_inflation_factor).round(0)

    return {
        "labels": [str(int(y)) for y in yearly["year"]],
        "raw": [int(v) for v in raw],
        "harmonized": [int(v) for v in harmonized],
        "unit": "fire events per year",
        "is_modeled": True,
        "modeled_note": (
            "Modelled baseline projection. The multi-year FIRMS archive has not been "
            "ingested yet; yearly values come from biome seasonal cycles and documented "
            "megafire years, not from measured detections."
        ),
        "inflation_factor_used": round(measured_inflation_factor, 3),
        "inflation_factor_source": (
            "Measured from paired fires in the ingested benchmark window: mean VIIRS "
            "detections per cross-sensor-confirmed fire divided by mean MODIS detections "
            "per cross-sensor-confirmed fire."
        ),
        "viirs_start_year": 2012,
    }


def main():
    print("=" * 78)
    print("BUILDING DASHBOARD DATA")
    print("=" * 78)

    with open(CLUSTER_REPORT) as f:
        cluster_report = json.load(f)
    with open(GA_REPORT) as f:
        ga_report = json.load(f)

    df = pd.read_csv(HARMONIZED_CSV)
    print(f"[✓] {len(df):,} consolidated fire events loaded")

    st = cluster_report["spatio_temporal_clusters"]
    sb = cluster_report["sensor_breakdown"]

    v_px = sb.get("mean_viirs_pixels_per_cross_sensor_fire") or 1.0
    m_px = sb.get("mean_modis_pixels_per_cross_sensor_fire") or 1.0
    inflation_factor = v_px / m_px

    dates = sorted(df["acq_date"].astype(str).unique())
    map_points, n_points = build_map_points(df)

    # Per-biome day coverage. The collector did not pull an equal window for every
    # region, and a biome with one day of data cannot support a seasonal claim, so the
    # gap is surfaced rather than averaged away.
    coverage = df.groupby("biome_name")["acq_date"].nunique().to_dict()
    short = {k: int(v) for k, v in coverage.items() if v < len(dates)}
    if short:
        print(f"[!] Uneven coverage — these biomes have fewer days than the window: {short}")

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": "EmberSync",
            "team": "Team ASL NOVA — Mymensingh Engineering College",
            "challenge": "Harmonization of MODIS and VIIRS Hot Spots",
            "event": "NASA International Space Apps Challenge 2026",
            "data_window": {"start": dates[0], "end": dates[-1], "days": len(dates)},
            "data_source": "NASA FIRMS active fire products (MODIS C6.1 NRT, VIIRS S-NPP 375 m NRT)",
            "total_raw_records": cluster_report["total_raw_records"],
            "total_fire_events": st["total_unique_physical_fires"],
            "inflation_removed_pct": st["overall_clustering_reduction_percentage"],
            "cross_sensor_matches": sb["clustered_cross_sensor_matches"],
            "mean_viirs_detections_per_fire": v_px,
            "mean_modis_detections_per_fire": m_px,
            "per_fire_count_inflation_factor": round(inflation_factor, 2),
            "map_points_shown": n_points,
            "note": (
                f"Validated on a {len(dates)}-day global benchmark window "
                f"({dates[0]} to {dates[-1]}) of {cluster_report['total_raw_records']:,} "
                "real NASA FIRMS detections. Multi-year archive ingestion is in progress; "
                "the 2000-2026 timeline on this page is a modelled projection, not "
                "measured data."
            ),
            "coverage_warning": (
                "Biome coverage is uneven in this window: "
                + "; ".join(f"{k} has {v} of {len(dates)} days" for k, v in sorted(short.items()))
                + ". Results for those biomes are provisional."
            ) if short else None,
            "calendar_baseline_caveat": (
                "Z-scores are computed against this benchmark window only. A meaningful "
                "climatological baseline requires the multi-year archive."
            ),
        },
        "sensor_split": {
            "MODIS": sb["raw_counts"].get("MODIS", 0),
            "VIIRS": sb["raw_counts"].get("VIIRS", 0),
            "viirs_to_modis_ratio": sb["viirs_to_modis_raw_ratio"],
        },
        "biomes": build_biomes(cluster_report, ga_report, coverage),
        "fire_points": map_points,
        "calendar": build_calendar(df),
        "raw_vs_harmonized": build_long_timeline(inflation_factor),
        "energy_totals": {
            "raw_sum_frp_mw": round(float(df["total_frp_mw"].sum()), 1),
            "representative_frp_mw": round(float(df["representative_frp_mw"].sum()), 1),
            "harmonized_frp_mw": round(float(df["harmonized_frp_mw"].sum()), 1),
            "events_calibrated": int(df["harmonization_applied"].sum()),
            "note": (
                "raw_sum double-counts fires seen by both satellites; representative "
                "avoids that; harmonized additionally maps VIIRS-only fires onto the "
                "MODIS energy scale."
            ),
        },
        "citations": [
            {"ref": "Giglio, Schroeder & Justice (2016), Remote Sensing of Environment",
             "note": "MODIS Collection 6 active fire product this pipeline builds on."},
            {"ref": "Li, Zhang, Kondragunta & Csiszar (2018), JGR Atmospheres",
             "note": "VIIRS vs MODIS FRP: ~20% systemic difference, growing at swath edges."},
            {"ref": "Fu et al. (2020)",
             "note": "MODIS misses a large share of VIIRS-detected fires in croplands and low-biomass land."},
        ],
        "team_members": [
            {"name": "Mosharrof Hossain", "role": "Team Lead & ML Engineer"},
            {"name": "Sabrina Akter Saba", "role": "Data Engineer"},
            {"name": "Tausif Mahdi Akanda", "role": "GIS & Visualization"},
            {"name": "Abu Shaed Khan", "role": "Full-stack Development"},
            {"name": "Sanjid Mahmud", "role": "Data Science"},
            {"name": "Bayezid Khan", "role": "Design & Storytelling"},
        ],
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)

    size_kb = os.path.getsize(OUT_JSON) / 1024
    print(f"[✓] {OUT_JSON}  ({size_kb:,.0f} KB)")
    print(f"    biomes          : {len(payload['biomes'])}")
    print(f"    map points      : {n_points:,} of {len(df):,} events")
    print(f"    calendar rows   : {len(payload['calendar'])}")
    print(f"    timeline years  : {len(payload['raw_vs_harmonized']['labels']) if payload['raw_vs_harmonized'] else 0} (modelled)")
    print(f"    inflation factor: {inflation_factor:.2f}x  ({v_px} VIIRS / {m_px} MODIS detections per confirmed fire)")


if __name__ == "__main__":
    main()
