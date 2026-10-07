#!/usr/bin/env python3
"""
EmberSync — Spatio-Temporal Clustering Core
NASA Space Apps Challenge 2026: Harmonization of MODIS and VIIRS Hot Spots

This module implements the Stage-1 clustering that consolidates multiple satellite
sub-pixel detections of a single physical fire into one fire event.

Scientific design decisions (and why):

1. EQUAL-GROUND-DISTANCE GRID (cos-latitude corrected)
   A naive lat/lon grid is not a constant ground distance: 0.01 deg of longitude is
   1.11 km at the equator but only ~0.56 km at 60 deg N. Since our archive spans
   Canada, Russia and Scandinavia as well as the Amazon, longitude is normalised by
   cos(latitude) so that a declared radius R really means R kilometres everywhere.

2. HAVERSINE ADJACENT-CELL MERGE
   Pure grid bucketing splits a fire that straddles a cell boundary into two events,
   which systematically UNDER-counts the redundancy we are trying to remove. After
   bucketing we therefore union neighbouring cells whose centroids lie within R km of
   each other, measured with the Haversine great-circle distance.

3. EXPLICIT TEMPORAL WINDOW
   Detections are grouped by acquisition date AND day/night overpass flag. The day and
   night overpass windows are each ~12 h, so this makes the declared 12-hour temporal
   window a real constraint rather than an unused constant. It also avoids conflating
   the diurnal fire cycle: a daytime and a night-time observation of the same location
   are separate physical observations, not duplicates.

4. PER-SENSOR ENERGY IS KEPT SEPARATE
   Summing MODIS FRP and VIIRS FRP for one fire double-counts its radiative energy.
   We therefore carry modis_frp_mw and viirs_frp_mw as separate columns. This is also
   what makes genuine cross-sensor calibration possible downstream: for a fire both
   satellites saw on the same day we have a true (VIIRS -> MODIS) observation pair.
"""

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0088
DEG_PER_KM = 1.0 / 111.32


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Accepts scalars or numpy arrays."""
    p1 = np.radians(lat1)
    p2 = np.radians(lat2)
    dphi = p2 - p1
    dlam = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


class _DisjointSet:
    """Union-find with path compression, used to merge adjacent grid cells."""

    def __init__(self):
        self.parent = {}

    def find(self, x):
        root = x
        while self.parent.get(root, root) != root:
            root = self.parent[root]
        while self.parent.get(x, x) != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def unify_brightness(df):
    """
    MODIS reports brightness in 'brightness' (band 21/22, K); VIIRS reports
    'bright_ti4' (I-4 band, K). Collapse them into one comparable column.
    """
    bright = pd.to_numeric(df.get("brightness"), errors="coerce")
    if "bright_ti4" in df.columns:
        ti4 = pd.to_numeric(df["bright_ti4"], errors="coerce")
        bright = bright.fillna(ti4)
    return bright.fillna(0.0)


def assign_clusters(df, radius_km):
    """
    Assign a cluster label to every detection in `df` for the given radius.

    Returns a pd.Series of integer cluster labels aligned to df.index.
    Expects columns: latitude, longitude, acq_date, daynight.
    """
    cell_deg = radius_km * DEG_PER_KM

    lat = df["latitude"].to_numpy(dtype=float)
    lon = df["longitude"].to_numpy(dtype=float)

    # Normalise longitude so one cell is `radius_km` of ground distance at any latitude.
    lon_norm = lon * np.cos(np.radians(lat))

    gy = np.floor(lat / cell_deg).astype(np.int64)
    gx = np.floor(lon_norm / cell_deg).astype(np.int64)

    work = pd.DataFrame(
        {
            "acq_date": df["acq_date"].astype(str).to_numpy(),
            "daynight": df["daynight"].fillna("D").astype(str).to_numpy(),
            "gx": gx,
            "gy": gy,
            "lat": lat,
            "lon": lon,
        },
        index=df.index,
    )

    # --- Pass 1: bucket into equal-ground-distance cells within one overpass window.
    keys = ["acq_date", "daynight", "gx", "gy"]
    work["cell_id"] = work.groupby(keys, sort=False).ngroup()

    # --- Pass 2: Haversine merge of neighbouring cells (fixes boundary splitting).
    cell_centroids = work.groupby("cell_id", sort=True).agg(
        acq_date=("acq_date", "first"),
        daynight=("daynight", "first"),
        gx=("gx", "first"),
        gy=("gy", "first"),
        lat=("lat", "mean"),
        lon=("lon", "mean"),
    )

    # Work on contiguous numpy arrays rather than pandas row lookups: cell_id comes
    # from ngroup() so it is already 0..n-1 and can index these directly. On a
    # multi-year archive this inner loop dominates, and per-row .loc access was
    # roughly two orders of magnitude slower.
    c_date = cell_centroids["acq_date"].to_numpy()
    c_dn = cell_centroids["daynight"].to_numpy()
    c_gx = cell_centroids["gx"].to_numpy(dtype=np.int64)
    c_gy = cell_centroids["gy"].to_numpy(dtype=np.int64)
    c_lat = cell_centroids["lat"].to_numpy(dtype=float)
    c_lon = cell_centroids["lon"].to_numpy(dtype=float)
    n_cells = len(cell_centroids)

    lookup = {
        (c_date[i], c_dn[i], c_gx[i], c_gy[i]): i for i in range(n_cells)
    }

    dsu = _DisjointSet()
    # Only half the neighbourhood is scanned; union is symmetric so this covers all pairs.
    neighbour_offsets = ((1, 0), (0, 1), (1, 1), (1, -1))

    src, dst = [], []
    for i in range(n_cells):
        for dx, dy in neighbour_offsets:
            j = lookup.get((c_date[i], c_dn[i], c_gx[i] + dx, c_gy[i] + dy))
            if j is not None:
                src.append(i)
                dst.append(j)

    if src:
        src = np.asarray(src)
        dst = np.asarray(dst)
        # One vectorised Haversine call for every candidate pair.
        within = haversine_km(c_lat[src], c_lon[src], c_lat[dst], c_lon[dst]) <= radius_km
        for i, j in zip(src[within], dst[within]):
            dsu.union(int(i), int(j))

    merged = work["cell_id"].map(dsu.find)
    # Re-label densely so cluster ids are contiguous 0..n-1
    return pd.factorize(merged)[0]


def aggregate_events(df, cluster_labels, class_id, class_name, id_offset=0):
    """
    Collapse detections into one row per physical fire event.

    Vectorised with groupby/agg — the previous row-by-row Python loop over groups
    was O(n_groups) interpreted iterations and would not finish on a multi-year
    global archive.
    """
    d = df.copy()
    d["_cluster"] = cluster_labels
    d["_bright"] = unify_brightness(d)
    d["_frp"] = pd.to_numeric(d["frp"], errors="coerce").fillna(0.0)

    base = d.groupby("_cluster", sort=True).agg(
        acq_date=("acq_date", "first"),
        center_latitude=("latitude", "mean"),
        center_longitude=("longitude", "mean"),
        pixel_detections_count=("_frp", "size"),
        total_frp_mw=("_frp", "sum"),
        max_brightness_k=("_bright", "max"),
        daynight=("daynight", "first"),
    )

    # Per-sensor energy and pixel counts — kept separate so the downstream genetic
    # algorithm can calibrate VIIRS against MODIS on genuinely paired observations.
    frp_by_sensor = d.pivot_table(
        index="_cluster", columns="source_sensor", values="_frp", aggfunc="sum"
    )
    px_by_sensor = d.pivot_table(
        index="_cluster", columns="source_sensor", values="_frp", aggfunc="size"
    )

    # Per-sensor peak brightness is kept separate too. Stage 2 predicts the MODIS
    # measurement from VIIRS observables, so feeding it a brightness that was maxed
    # over BOTH sensors would leak the target into the predictors.
    bright_by_sensor = d.pivot_table(
        index="_cluster", columns="source_sensor", values="_bright", aggfunc="max"
    )

    for sensor, col in (("MODIS", "modis"), ("VIIRS", "viirs")):
        base[f"{col}_frp_mw"] = (
            frp_by_sensor[sensor] if sensor in frp_by_sensor else 0.0
        )
        base[f"{col}_pixels"] = (
            px_by_sensor[sensor] if sensor in px_by_sensor else 0.0
        )
        base[f"{col}_max_brightness_k"] = (
            bright_by_sensor[sensor] if sensor in bright_by_sensor else 0.0
        )
    base[["modis_max_brightness_k", "viirs_max_brightness_k"]] = base[
        ["modis_max_brightness_k", "viirs_max_brightness_k"]
    ].fillna(0.0)
    base[["modis_frp_mw", "viirs_frp_mw"]] = base[
        ["modis_frp_mw", "viirs_frp_mw"]
    ].fillna(0.0)
    base[["modis_pixels", "viirs_pixels"]] = (
        base[["modis_pixels", "viirs_pixels"]].fillna(0).astype(int)
    )

    base["cross_sensor_validated"] = (base["modis_pixels"] > 0) & (
        base["viirs_pixels"] > 0
    )
    base["sensor_type"] = np.where(
        base["cross_sensor_validated"],
        "MODIS+VIIRS",
        np.where(base["modis_pixels"] > 0, "MODIS", "VIIRS"),
    )

    # Non-double-counted energy: when both sensors saw the fire, MODIS is the
    # harmonization baseline, so its measurement represents the event. Summing both
    # sensors (as the first version did) inflates radiative energy rather than
    # conserving it.
    base["representative_frp_mw"] = np.where(
        base["modis_frp_mw"] > 0, base["modis_frp_mw"], base["viirs_frp_mw"]
    )

    base = base.reset_index(drop=True)
    base.insert(0, "fire_event_id", [f"FIRE_{id_offset + i + 1:07d}" for i in range(len(base))])
    base.insert(4, "fire_class_id", class_id)
    base.insert(5, "biome_name", class_name)

    for c in ("center_latitude", "center_longitude"):
        base[c] = base[c].round(5)
    for c in (
        "total_frp_mw",
        "representative_frp_mw",
        "modis_frp_mw",
        "viirs_frp_mw",
        "max_brightness_k",
        "modis_max_brightness_k",
        "viirs_max_brightness_k",
    ):
        base[c] = base[c].round(2)

    return base
