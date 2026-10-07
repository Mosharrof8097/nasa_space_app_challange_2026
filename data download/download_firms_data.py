#!/usr/bin/env python3
"""
NASA FIRMS Active Fire Data Downloader
Specialized for NASA Space Apps Challenge 2026: Harmonization of MODIS and VIIRS Hot Spots.

Sources:
- MODIS: Terra & Aqua (1km)
- VIIRS: Suomi-NPP (375m) & NOAA-20 (375m)
"""

import os
import sys
import argparse
import requests
import pandas as pd
from datetime import datetime

# Default Bounding Box for Bangladesh [min_lon, min_lat, max_lon, max_lat]
BD_BBOX = "88.0,20.5,92.7,26.6"
DEFAULT_COUNTRY = "BGD"

SENSORS = {
    "MODIS": "MODIS_NRT",
    "VIIRS_SNPP": "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20": "VIIRS_NOAA20_NRT"
}

def create_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "raw_data")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def download_firms_api(map_key: str, sensor_id: str, area_or_country: str, days: int = 10, is_country: bool = False):
    """
    Downloads active fire CSV from NASA FIRMS API.
    """
    base_url = "https://firms.modaps.eosdis.nasa.gov/api"
    endpoint_type = "country" if is_country else "area"
    url = f"{base_url}/{endpoint_type}/csv/{map_key}/{sensor_id}/{area_or_country}/{days}"
    
    print(f"[*] Requesting {sensor_id} data from NASA FIRMS...")
    print(f"    URL: {url.replace(map_key, 'MAP_KEY_HIDDEN')}")
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.text.strip()
            if content.startswith("Invalid MAP_KEY"):
                print("[!] Error: Invalid NASA FIRMS MAP_KEY provided.")
                return None
            if "latitude" not in content and "longitude" not in content:
                print(f"[!] Warning: No hotspot data returned or empty response: {content[:150]}")
                return None
            return content
        else:
            print(f"[!] HTTP Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[!] Network error: {e}")
        return None

def save_csv_and_summarize(csv_text: str, sensor_name: str, output_dir: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f"{sensor_name}_{timestamp}.csv")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(csv_text)
    
    # Analyze with pandas
    from io import StringIO
    df = pd.read_csv(StringIO(csv_text))
    print(f"[✓] Saved {len(df)} records to: {file_path}")
    if len(df) > 0 and 'frp' in df.columns:
        print(f"    - Date Range: {df['acq_date'].min()} to {df['acq_date'].max()}")
        print(f"    - Total FRP (Fire Radiative Power): {df['frp'].sum():.2f} MW")
        print(f"    - Avg FRP per hotspot: {df['frp'].mean():.2f} MW")
    return file_path

def generate_sample_harmonization_data(output_dir: str):
    """
    Creates a sample Bangladesh dataset (MODIS & VIIRS) for testing harmonization algorithms
    in case user is waiting for NASA MAP_KEY email.
    """
    print("[*] Generating realistic sample Bangladesh calibration dataset for rapid offline testing...")
    
    # 1. Sample MODIS
    modis_data = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight
22.356,89.123,312.4,1.0,1.0,2024-03-15,0430,Terra,75,6.1NRT,298.1,18.5,D
22.360,89.130,318.1,1.0,1.0,2024-03-15,0430,Terra,82,6.1NRT,300.2,24.1,D
24.890,91.870,309.8,1.1,1.0,2024-03-20,0815,Aqua,65,6.1NRT,295.4,12.0,D
23.120,90.450,325.0,1.0,1.0,2024-04-02,0425,Terra,90,6.1NRT,302.0,35.6,D
21.450,92.200,314.5,1.0,1.0,2024-04-10,0820,Aqua,70,6.1NRT,297.8,19.2,D
"""
    # 2. Sample VIIRS (Higher resolution, detects smaller sub-pixels for same fire spots)
    viirs_data = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
22.355,89.121,330.2,0.38,0.38,2024-03-15,0715,N,nominal,2.0NRT,299.1,6.8,D
22.357,89.124,335.8,0.38,0.38,2024-03-15,0715,N,high,2.0NRT,301.0,11.2,D
22.359,89.129,328.4,0.38,0.38,2024-03-15,0715,N,nominal,2.0NRT,298.5,5.4,D
22.361,89.131,340.1,0.38,0.38,2024-03-15,0715,N,high,2.0NRT,303.2,14.6,D
24.889,91.868,322.5,0.39,0.38,2024-03-20,0720,N,nominal,2.0NRT,296.0,4.8,D
24.891,91.872,326.1,0.39,0.38,2024-03-20,0720,N,nominal,2.0NRT,297.1,7.2,D
23.119,90.448,345.0,0.38,0.38,2024-04-02,0710,N,high,2.0NRT,304.5,22.0,D
23.121,90.452,342.3,0.38,0.38,2024-04-02,0710,N,high,2.0NRT,303.8,16.5,D
21.448,92.198,329.0,0.40,0.38,2024-04-10,0725,N,nominal,2.0NRT,298.2,9.1,D
21.452,92.202,331.4,0.40,0.38,2024-04-10,0725,N,nominal,2.0NRT,299.0,10.5,D
"""
    m_path = os.path.join(output_dir, "sample_MODIS_Bangladesh.csv")
    v_path = os.path.join(output_dir, "sample_VIIRS_Bangladesh.csv")
    
    with open(m_path, "w") as f:
        f.write(modis_data.strip())
    with open(v_path, "w") as f:
        f.write(viirs_data.strip())
        
    print(f"[✓] Created sample dataset:\n    -> {m_path}\n    -> {v_path}")

def main():
    parser = argparse.ArgumentParser(description="Download NASA FIRMS Fire Data (MODIS & VIIRS)")
    parser.add_argument("--key", type=str, help="Your NASA FIRMS MAP_KEY (get free from https://firms.modaps.eosdis.nasa.gov/api/map_key/)")
    parser.add_argument("--country", type=str, default=DEFAULT_COUNTRY, help="Country ISO3 code (default: BGD for Bangladesh)")
    parser.add_argument("--bbox", type=str, default=BD_BBOX, help="Bounding box min_lon,min_lat,max_lon,max_lat")
    parser.add_argument("--days", type=int, default=10, help="Number of past days (1 to 10)")
    parser.add_argument("--sample", action="store_true", help="Generate sample dataset for rapid local testing")
    
    args = parser.parse_args()
    output_dir = create_directories()
    
    if args.sample or not args.key:
        if not args.key:
            print("\n" + "="*70)
            print("(!) NOTICE: No NASA FIRMS MAP_KEY provided.")
            print("    To download live data:")
            print("    1. Get a free instant key: https://firms.modaps.eosdis.nasa.gov/api/map_key/")
            print("    2. Run: python download_firms_data.py --key YOUR_KEY")
            print("    Generating offline sample dataset for immediate testing now...")
            print("="*70 + "\n")
        generate_sample_harmonization_data(output_dir)
        return

    # Download with provided key
    for name, sensor_code in SENSORS.items():
        # Try area bbox first (most reliable for regional subsets)
        csv_data = download_firms_api(args.key, sensor_code, args.bbox, days=args.days, is_country=False)
        if not csv_data:
            # Fallback to country code
            csv_data = download_firms_api(args.key, sensor_code, args.country, days=args.days, is_country=True)
            
        if csv_data:
            save_csv_and_summarize(csv_data, f"{name}_{args.country}", output_dir)
        else:
            print(f"[!] Failed to download {name}.")

if __name__ == "__main__":
    main()
