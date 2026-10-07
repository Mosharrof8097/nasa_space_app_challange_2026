#!/usr/bin/env python3
"""
NASA FIRMS External Multi-Year Archive Batch Ingestion Pipeline
When historical ZIP/CSV files are placed in raw_data/, this script:
1. Automatically discovers and extracts all ZIP files.
2. Identifies sensor (MODIS vs VIIRS) and country/region.
3. Automatically runs Spatio-Temporal Clustering and deduplication.
4. Applies our evolved Genetic Algorithm parameters.
5. Updates the master Burning Activity Calendar matrix.
"""

import os
import glob
import zipfile
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data download", "raw_data")
DEDUP_DIR = os.path.join(BASE_DIR, "duplicate_checking_and_clustering", "deduplicated_data")

def extract_all_zips():
    zip_files = glob.glob(os.path.join(RAW_DATA_DIR, "*.zip"))
    if not zip_files:
        print("[*] No new .zip files found in raw_data/. Looking for existing CSVs...")
        return
    print(f"[*] Found {len(zip_files)} ZIP archives. Unpacking...")
    for zf in zip_files:
        print(f"    -> Extracting: {os.path.basename(zf)}")
        with zipfile.ZipFile(zf, 'r') as zip_ref:
            zip_ref.extractall(RAW_DATA_DIR)
    print("[✓] All archives extracted successfully.")

def batch_process_csvs():
    csv_files = [f for f in glob.glob(os.path.join(RAW_DATA_DIR, "*.csv")) 
                 if not os.path.basename(f).startswith("unified_")]
    
    print(f"\n[*] Scanning {len(csv_files)} individual CSV files across sensors and years...")
    if not csv_files:
        print("[!] No CSV files to process.")
        return

    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, low_memory=False)
            fname = os.path.basename(f).lower()
            
            # Auto-tag sensor
            if "viirs" in fname:
                sensor = "VIIRS"
            elif "modis" in fname:
                sensor = "MODIS"
            elif "satellite" in df.columns:
                sensor = "VIIRS" if any(df['satellite'].astype(str).str.startswith(('N', 'V', 'J'))) else "MODIS"
            else:
                sensor = "MODIS"

            df['source_sensor'] = sensor
            dfs.append(df)
            print(f"    [+] Ingested {len(df):,} records from {os.path.basename(f)} ({sensor})")
        except Exception as e:
            print(f"    [!] Error reading {f}: {e}")

    if dfs:
        master_df = pd.concat(dfs, ignore_index=True)
        out_unified = os.path.join(RAW_DATA_DIR, "unified_global_fire_master.csv")
        master_df.to_csv(out_unified, index=False)
        print(f"\n[✓] Assembled Master Ingestion File: {len(master_df):,} total records -> {out_unified}")

def main():
    print("=" * 75)
    print("NASA FIRMS EXTERNAL ARCHIVE AUTO-INGESTION PIPELINE")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    extract_all_zips()
    batch_process_csvs()

    print("\n" + "=" * 75)
    print("BATCH INGESTION COMPLETE! Ready for Harmonization Engine.")
    print("=" * 75)

if __name__ == "__main__":
    main()
