#!/usr/bin/env python3
"""
Complete 4-Class Global Dataset Builder
Combines verified NASA FIRMS live downloads into authentic datasets for all 4 classes:
1. Montane & Hills (USA West / Sierra Nevada)
2. Dense Rainforest (Amazon Basin / Brazil)
3. Agricultural Plains (South Asia / Indo-Gangetic & Bangladesh)
4. Savannas & Grasslands (Southern Africa)
"""

import os
import io
import json
import subprocess
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "raw_data")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

STEPS_DIR = "/home/mosharrof/.gemini/antigravity/brain/1219aae5-7974-4dfc-a86d-6f81963d198f/.system_generated/steps"

def load_markdown_csv(file_path: str) -> pd.DataFrame:
    """Reads a CSV embedded after markdown headers."""
    if not os.path.exists(file_path):
        return pd.DataFrame()
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Find start of CSV (line containing 'latitude,longitude')
    start_idx = 0
    for idx, line in enumerate(lines[:30]):
        if "latitude,longitude" in line:
            start_idx = idx
            break
    csv_text = "".join(lines[start_idx:])
    return pd.read_csv(io.StringIO(csv_text))

def fetch_stream_csv(url: str, max_lines: int = 15000) -> pd.DataFrame:
    """Stream top N lines of CSV directly via curl."""
    print(f"[*] Streaming {url} (up to {max_lines} lines)...")
    cmd = f"curl -sL --max-time 45 '{url}' | head -n {max_lines}"
    res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.stdout:
        return pd.read_csv(io.StringIO(res.stdout))
    return pd.DataFrame()

def main():
    print("=" * 70)
    print("BUILDING COMPLETE AUTHENTIC 4-CLASS NASA FIRMS DATASET")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    summary = {
        "built_at": datetime.now().isoformat(),
        "classes": {}
    }
    all_dfs = []

    # -------------------------------------------------------------
    # CLASS 1: Montane & Hills (Western USA)
    # -------------------------------------------------------------
    print("\n>>> [1/4] Class 1: Montane & Hills")
    c1_summary = {"id": 1, "name": "Montane & Hills", "sensors": {}}
    
    # MODIS
    modis_c1_path = os.path.join(RAW_DATA_DIR, "raw_montane_hills_MODIS.csv")
    if os.path.exists(modis_c1_path):
        df_c1_m = pd.read_csv(modis_c1_path)
    else:
        df_c1_m = pd.DataFrame()
    
    # VIIRS (From step 48)
    df_usa_v = load_markdown_csv(os.path.join(STEPS_DIR, "48/content.md"))
    df_c1_v = df_usa_v[(df_usa_v['longitude'] <= -110.0) & (df_usa_v['latitude'] >= 32.0)].copy()
    df_c1_v["source_sensor"] = "VIIRS"
    df_c1_v["fire_class_id"] = 1
    df_c1_v["biome_name"] = "Montane & Hills"
    df_c1_v.to_csv(os.path.join(RAW_DATA_DIR, "raw_montane_hills_VIIRS.csv"), index=False)

    c1_summary["sensors"]["MODIS"] = {"records": len(df_c1_m), "total_frp_mw": round(float(df_c1_m['frp'].sum()), 1), "file": "raw_montane_hills_MODIS.csv"}
    c1_summary["sensors"]["VIIRS"] = {"records": len(df_c1_v), "total_frp_mw": round(float(df_c1_v['frp'].sum()), 1), "file": "raw_montane_hills_VIIRS.csv"}
    print(f"    - MODIS: {len(df_c1_m):,} points (FRP: {df_c1_m['frp'].sum():,.1f} MW)")
    print(f"    - VIIRS: {len(df_c1_v):,} points (FRP: {df_c1_v['frp'].sum():,.1f} MW)")
    summary["classes"]["montane_hills"] = c1_summary
    all_dfs.extend([df_c1_m, df_c1_v])

    # -------------------------------------------------------------
    # CLASS 2: Dense Rainforest (Amazon Basin)
    # -------------------------------------------------------------
    print("\n>>> [2/4] Class 2: Dense Rainforest (Amazon Basin)")
    c2_summary = {"id": 2, "name": "Dense Rainforest", "sensors": {}}
    
    # MODIS (From step 52)
    df_sa_m = load_markdown_csv(os.path.join(STEPS_DIR, "52/content.md"))
    df_c2_m = df_sa_m[(df_sa_m['longitude'] >= -74.0) & (df_sa_m['longitude'] <= -44.0) & (df_sa_m['latitude'] >= -18.0) & (df_sa_m['latitude'] <= 5.0)].copy()
    df_c2_m["source_sensor"] = "MODIS"
    df_c2_m["fire_class_id"] = 2
    df_c2_m["biome_name"] = "Dense Rainforest"
    df_c2_m.to_csv(os.path.join(RAW_DATA_DIR, "raw_dense_rainforest_MODIS.csv"), index=False)

    # VIIRS (From step 56)
    df_sa_v = load_markdown_csv(os.path.join(STEPS_DIR, "56/content.md"))
    df_c2_v = df_sa_v[(df_sa_v['longitude'] >= -74.0) & (df_sa_v['longitude'] <= -44.0) & (df_sa_v['latitude'] >= -18.0) & (df_sa_v['latitude'] <= 5.0)].copy()
    df_c2_v["source_sensor"] = "VIIRS"
    df_c2_v["fire_class_id"] = 2
    df_c2_v["biome_name"] = "Dense Rainforest"
    df_c2_v.to_csv(os.path.join(RAW_DATA_DIR, "raw_dense_rainforest_VIIRS.csv"), index=False)

    c2_summary["sensors"]["MODIS"] = {"records": len(df_c2_m), "total_frp_mw": round(float(df_c2_m['frp'].sum()), 1), "file": "raw_dense_rainforest_MODIS.csv"}
    c2_summary["sensors"]["VIIRS"] = {"records": len(df_c2_v), "total_frp_mw": round(float(df_c2_v['frp'].sum()), 1), "file": "raw_dense_rainforest_VIIRS.csv"}
    print(f"    - MODIS: {len(df_c2_m):,} points (FRP: {df_c2_m['frp'].sum():,.1f} MW)")
    print(f"    - VIIRS: {len(df_c2_v):,} points (FRP: {df_c2_v['frp'].sum():,.1f} MW)")
    summary["classes"]["dense_rainforest"] = c2_summary
    all_dfs.extend([df_c2_m, df_c2_v])

    # -------------------------------------------------------------
    # CLASS 3: Agricultural Plains (South Asia & Bangladesh)
    # -------------------------------------------------------------
    print("\n>>> [3/4] Class 3: Agricultural Plains")
    c3_summary = {"id": 3, "name": "Agricultural Plains", "sensors": {}}
    df_c3_m = pd.read_csv(os.path.join(RAW_DATA_DIR, "raw_agricultural_plains_MODIS.csv"))
    df_c3_v = pd.read_csv(os.path.join(RAW_DATA_DIR, "raw_agricultural_plains_VIIRS.csv"))
    c3_summary["sensors"]["MODIS"] = {"records": len(df_c3_m), "total_frp_mw": round(float(df_c3_m['frp'].sum()), 1), "file": "raw_agricultural_plains_MODIS.csv"}
    c3_summary["sensors"]["VIIRS"] = {"records": len(df_c3_v), "total_frp_mw": round(float(df_c3_v['frp'].sum()), 1), "file": "raw_agricultural_plains_VIIRS.csv"}
    print(f"    - MODIS: {len(df_c3_m):,} points (FRP: {df_c3_m['frp'].sum():,.1f} MW)")
    print(f"    - VIIRS: {len(df_c3_v):,} points (FRP: {df_c3_v['frp'].sum():,.1f} MW)")
    summary["classes"]["agricultural_plains"] = c3_summary
    all_dfs.extend([df_c3_m, df_c3_v])

    # -------------------------------------------------------------
    # CLASS 4: Savannas & Grasslands (Southern Africa)
    # -------------------------------------------------------------
    print("\n>>> [4/4] Class 4: Savannas & Grasslands (Southern Africa)")
    c4_summary = {"id": 4, "name": "Savannas & Grasslands", "sensors": {}}
    
    url_af_m = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Southern_Africa_7d.csv"
    url_af_v = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Southern_Africa_7d.csv"
    
    df_c4_m = fetch_stream_csv(url_af_m, max_lines=6000)
    df_c4_m["source_sensor"] = "MODIS"
    df_c4_m["fire_class_id"] = 4
    df_c4_m["biome_name"] = "Savannas & Grasslands"
    df_c4_m.to_csv(os.path.join(RAW_DATA_DIR, "raw_savannas_grasslands_MODIS.csv"), index=False)

    df_c4_v = fetch_stream_csv(url_af_v, max_lines=15000)
    df_c4_v["source_sensor"] = "VIIRS"
    df_c4_v["fire_class_id"] = 4
    df_c4_v["biome_name"] = "Savannas & Grasslands"
    df_c4_v.to_csv(os.path.join(RAW_DATA_DIR, "raw_savannas_grasslands_VIIRS.csv"), index=False)

    c4_summary["sensors"]["MODIS"] = {"records": len(df_c4_m), "total_frp_mw": round(float(df_c4_m['frp'].sum()), 1), "file": "raw_savannas_grasslands_MODIS.csv"}
    c4_summary["sensors"]["VIIRS"] = {"records": len(df_c4_v), "total_frp_mw": round(float(df_c4_v['frp'].sum()), 1), "file": "raw_savannas_grasslands_VIIRS.csv"}
    print(f"    - MODIS: {len(df_c4_m):,} points (FRP: {df_c4_m['frp'].sum():,.1f} MW)")
    print(f"    - VIIRS: {len(df_c4_v):,} points (FRP: {df_c4_v['frp'].sum():,.1f} MW)")
    summary["classes"]["savannas_grasslands"] = c4_summary
    all_dfs.extend([df_c4_m, df_c4_v])

    # -------------------------------------------------------------
    # UNIFIED GLOBAL DATASET
    # -------------------------------------------------------------
    print("\n[*] Assembling Consolidated Unified Global 4-Class Dataset...")
    unified_df = pd.concat(all_dfs, ignore_index=True)
    unified_path = os.path.join(RAW_DATA_DIR, "unified_global_fire_7d.csv")
    unified_df.to_csv(unified_path, index=False)
    summary["total_hotspots_collected"] = len(unified_df)
    print(f"[✓] Saved Unified Dataset: {len(unified_df):,} TOTAL HOTSPOTS -> unified_global_fire_7d.csv")

    summary_path = os.path.join(RAW_DATA_DIR, "collection_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[✓] Saved metadata summary to: {summary_path}")

    print("\n" + "=" * 70)
    print("ALL 4 CLASSES FULLY POPULATED WITH AUTHENTIC NASA SATELLITE DATA!")
    print("=" * 70)

if __name__ == "__main__":
    main()
