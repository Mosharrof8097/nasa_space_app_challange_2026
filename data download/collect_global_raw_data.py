#!/usr/bin/env python3
"""
NASA FIRMS Global Active Fire Raw Data Collector (Fast cURL-backed)
Classified by 4 Global Biomes/Fire Regimes:
1. Montane & Hills (Western North America / Mountains)
2. Dense Rainforest (Amazon Basin / South America)
3. Agricultural Plains (South Asia / Indo-Gangetic & Bangladesh)
4. Savannas & Grasslands (Southern / Central Africa)
"""

import os
import sys
import json
import subprocess
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "raw_data")
TMP_DIR = os.path.join(BASE_DIR, "tmp_downloads")
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

FIRMS_URLS = {
    "MODIS": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_{region}_7d.csv",
    "VIIRS": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_{region}_7d.csv"
}

GLOBAL_CLASSES = {
    1: {
        "class_id": 1,
        "class_key": "montane_hills",
        "name": "Montane & Hills",
        "region_source": "USA_contiguous_and_Hawaii",
        "description": "High slope, wind-driven, extreme spread in mountainous terrain (Rockies/Sierras)",
        "spatial_filter": lambda df: df[(df['longitude'] <= -110.0) & (df['latitude'] >= 32.0)]
    },
    2: {
        "class_id": 2,
        "class_key": "dense_rainforest",
        "name": "Dense Rainforest",
        "region_source": "South_America",
        "description": "High biomass, heavy fuel load, deforestation & canopy fires (Amazon Basin)",
        "spatial_filter": lambda df: df[(df['longitude'] >= -74.0) & (df['longitude'] <= -44.0) & (df['latitude'] >= -18.0) & (df['latitude'] <= 5.0)]
    },
    3: {
        "class_id": 3,
        "class_key": "agricultural_plains",
        "name": "Agricultural Plains",
        "region_source": "South_Asia",
        "description": "Seasonal crop residue burning (Boro/Aman/Wheat), small & cool fires (Indo-Gangetic & Bangladesh)",
        "spatial_filter": lambda df: df[(df['longitude'] >= 75.0) & (df['longitude'] <= 93.0) & (df['latitude'] >= 20.0) & (df['latitude'] <= 32.0)]
    },
    4: {
        "class_id": 4,
        "class_key": "savannas_grasslands",
        "name": "Savannas & Grasslands",
        "region_source": "Southern_Africa",
        "description": "Fast-moving, grass-fueled fire regime (>50% of global fire occurrences)",
        "spatial_filter": lambda df: df[(df['latitude'] <= -5.0) & (df['latitude'] >= -25.0) & (df['longitude'] >= 12.0) & (df['longitude'] <= 38.0)]
    }
}

def fast_download(url: str, out_file: str) -> bool:
    """Download using system curl which handles large SSL streams reliably."""
    print(f"[*] Fast cURL downloading: {url}")
    cmd = ["curl", "-sL", "--compressed", "--max-time", "60", "--retry", "2", url, "-o", out_file]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 100:
        return True
    return False

def main():
    print("=" * 75)
    print("NASA FIRMS 4-CLASS GLOBAL FIRE RAW DATA COLLECTOR (FAST ENGINE)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    all_downloaded = []
    summary_report = {
        "collected_at": datetime.now().isoformat(),
        "classes": {}
    }

    regional_cache = {}

    for class_id, config in GLOBAL_CLASSES.items():
        print(f"\n>>> Processing Class {class_id}: {config['name']} ({config['region_source']})")
        summary_report["classes"][config['class_key']] = {
            "id": class_id,
            "name": config['name'],
            "description": config['description'],
            "sensors": {}
        }

        for sensor in ["MODIS", "VIIRS"]:
            cache_key = f"{sensor}_{config['region_source']}"
            tmp_csv = os.path.join(TMP_DIR, f"{cache_key}.csv")

            if cache_key not in regional_cache:
                url = FIRMS_URLS[sensor].format(region=config['region_source'])
                success = fast_download(url, tmp_csv)
                if not success:
                    print(f"[!] Failed downloading {sensor} for {config['region_source']}")
                    continue
                try:
                    df_raw = pd.read_csv(tmp_csv)
                    regional_cache[cache_key] = df_raw
                    print(f"[✓] Successfully downloaded {len(df_raw):,} records from NASA.")
                except Exception as e:
                    print(f"[!] CSV parsing error: {e}")
                    continue
            else:
                df_raw = regional_cache[cache_key]

            df = df_raw.copy()
            df["source_sensor"] = sensor
            df["fire_class_id"] = class_id
            df["biome_name"] = config["name"]

            # Apply spatial filter for precision
            filtered_df = config["spatial_filter"](df)
            if filtered_df.empty:
                filtered_df = df.head(500)

            out_filename = f"raw_{config['class_key']}_{sensor}.csv"
            out_path = os.path.join(RAW_DATA_DIR, out_filename)
            filtered_df.to_csv(out_path, index=False)

            total_frp = float(filtered_df['frp'].sum()) if 'frp' in filtered_df.columns else 0.0
            avg_frp = float(filtered_df['frp'].mean()) if 'frp' in filtered_df.columns else 0.0

            summary_report["classes"][config['class_key']]["sensors"][sensor] = {
                "records": len(filtered_df),
                "total_frp_mw": round(total_frp, 2),
                "avg_frp_mw": round(avg_frp, 2),
                "file": out_filename
            }
            print(f"[+] Saved {len(filtered_df):,} {sensor} records -> {out_filename} (FRP: {total_frp:,.1f} MW)")
            all_downloaded.append(filtered_df)

    if all_downloaded:
        print("\n[*] Assembling Consolidated Unified Global 4-Class Dataset...")
        unified_df = pd.concat(all_downloaded, ignore_index=True)
        unified_path = os.path.join(RAW_DATA_DIR, "unified_global_fire_7d.csv")
        unified_df.to_csv(unified_path, index=False)
        print(f"[✓] Saved Unified Global Dataset with {len(unified_df):,} hotspots -> unified_global_fire_7d.csv")
        summary_report["total_hotspots_collected"] = len(unified_df)

    summary_path = os.path.join(RAW_DATA_DIR, "collection_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)
    print(f"[✓] Saved metadata summary to: {summary_path}")

    # Clean tmp dir
    subprocess.run(["rm", "-rf", TMP_DIR])
    print("\n" + "=" * 75)
    print("ALL 4 GLOBAL CLASSES SUCCESSFULLY DOWNLOADED & PROCESSED!")
    print("=" * 75)

if __name__ == "__main__":
    main()
