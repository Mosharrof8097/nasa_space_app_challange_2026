# NASA FIRMS Active Fire Data Download Guide (Bangladesh & Custom AOI)

এই গাইডটিতে NASA-এর অফিসিয়াল উৎস থেকে **MODIS** এবং **VIIRS** ফায়ার ডেটাসেট নির্ভুলভাবে ডাউনলোড করার সম্পূর্ণ প্রক্রিয়া বিস্তারিত বর্ণনা করা হয়েছে।

---

## ১. অফিশিয়াল ডেটাসেট পরিচিতি (Official Datasets)

এই চ্যালেঞ্জের মূল লক্ষ্য হলো **MODIS** এবং **VIIRS** সেন্সরের ডেটা হারমোনাইজ করা।

| স্যাটেলাইট সেন্সর | রেজোলিউশন | সময়কাল | প্রোডাক্ট কোড | মূল ব্যবহার |
| :--- | :--- | :--- | :--- | :--- |
| **MODIS (Terra & Aqua)** | ১ কিমি (1 km) | ২০০০ – বর্তমান | `MCD14DL` | দীর্ঘমেয়াদী ২০+ বছরের ঐতিহাসিক বেসলাইন |
| **VIIRS (Suomi-NPP)** | ৩৭৫ মি (375 m) | ২০১২ – বর্তমান | `VNP14IMGTDL` | উচ্চ রেজোলিউশনের আধুনিক ফায়ার ডেটা |
| **VIIRS (NOAA-20 / J1)** | ৩৭৫ মি (375 m) | ২০২০ – বর্তমান | `VJ114IMGTDL` | পরিপূরক আধুনিক ফায়ার ডেটা |

---

## ২. ডেটা সংগ্রহের ২টি অফিশিয়াল মাধ্যম

### মাধ্যম ক: NASA FIRMS Web Archive Tool (পুরো ২০ বছরের ডেটার জন্য সবচেয়ে সেরা)

আপনি যদি ২০০০ থেকে ২০২৫ পর্যন্ত সমস্ত ঐতিহাসিক ডেটা একবারে ডাউনলোড করতে চান:

1. **Earthdata অ্যাকাউন্ট তৈরি করুন:**
   * যান: [https://urs.earthdata.nasa.gov/](https://urs.earthdata.nasa.gov/) এবং একটি ফ্রি একাউন্ট খুলুন।
2. **FIRMS Download পোর্টালে যান:**
   * যান: [https://firms.modaps.eosdis.nasa.gov/download/](https://firms.modaps.eosdis.nasa.gov/download/)
3. **প্যারামিটার সিলেক্ট করুন:**
   * **Region:** Countryভিত্তিক `Bangladesh` সিলেক্ট করুন (অথবা Custom Coordinates: `88.0, 20.5, 92.7, 26.6`)।
   * **Sensor:** 
     1. প্রথমে `MODIS Standard Quality (2000-present)` ডাউনলোড করুন।
     2. এরপর `VIIRS S-NPP 375m (2012-present)` ডাউনলোড করুন।
   * **Format:** `CSV` সিলেক্ট করুন (ক্যালকুলেশন ও কোডিংয়ের জন্য CSV সবচেয়ে হালকা ও দ্রুত কাজ করে)।
4. আপনার ইমেইলে ডাউনলোডের সরাসরি লিঙ্ক চলে আসবে (সাধারণত ২-৫ মিনিটের মধ্যে)।

---

### মাধ্যম খ: NASA FIRMS API (অটোমেটেড ডাউনলোড স্ক্রিপ্ট)

আপনি যদি সরাসরি পাইথন স্ক্রিপ্ট দিয়ে কোডের মাধ্যমে ডেটা নামাতে চান:

1. **ফ্রি MAP_KEY সংগ্রহ করুন:**
   * যান: [https://firms.modaps.eosdis.nasa.gov/api/map_key/](https://firms.modaps.eosdis.nasa.gov/api/map_key/)
   * আপনার ইমেইল প্রদান করুন। ১ মিনিটের মধ্যে NASA আপনাকে একটি ইউনিক ৩০-ক্যারেক্টারের `MAP_KEY` ইমেইল করবে।
2. **API Endpoint ফরম্যাট:**
   * কান্ট্রি অনুযায়ী ডেটা:
     ```
     https://firms.modaps.eosdis.nasa.gov/api/country/csv/[MAP_KEY]/[SENSOR]/BGD/[DAYS]
     ```
   * বাউন্ডিং বক্স (Area) অনুযায়ী ডেটা:
     ```
     https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SENSOR]/88.0,20.5,92.7,26.6/[DAYS]
     ```

---

## ৩. গুরুত্বপূর্ণ কলামসমূহ (Data Columns Definition)

ডাউনলোডকৃত CSV ফাইলে নিম্নোক্ত কলামগুলো থাকবে:

* **latitude, longitude:** আগুনের কেন্দ্রস্থলের ভৌগোলিক স্থানাঙ্ক।
* **brightness / bright_ti4:** কেলভিন (K) এককে ব্রাইটনেস টেম্পারেচার।
* **scan, track:** স্যাটেলাইটের পিক্সেল সাইজ ও স্ক্যান স্পেসিফিকেশন।
* **acq_date:** অগ্নিকাণ্ড শনাক্তের তারিখ (YYYY-MM-DD)।
* **acq_time:** শনাক্তের সময় (UTC)।
* **satellite:** কোন স্যাটেলাইট শনাক্ত করেছে (`Terra`, `Aqua`, `N` for Suomi-NPP)।
* **confidence:** ডিটেকশন আত্মবিশ্বাসের মাত্রা (MODIS: 0-100%, VIIRS: low, nominal, high)।
* **frp (Fire Radiative Power):** মেগাওয়াট (MW) এককে নির্গত তাপশক্তি। **(হারমোনাইজেশনের জন্য সবচেয়ে গুরুত্বপূর্ণ প্যারামিটার)**।
* **daynight:** দিনের বেলার আগুন নাকি রাতের (`D` = Day, `N` = Night)।

---

## ৪. স্ক্রিপ্টটি কীভাবে চালাবেন?

এই ফোল্ডারে থাকা `download_firms_data.py` স্ক্রিপ্টটি রান করতে:

```bash
# ডিপেন্ডেন্সি ইনস্টল (যদি না থাকে)
pip install requests pandas

# আপনার MAP_KEY দিয়ে রান করুন
python download_firms_data.py --key YOUR_NASA_MAP_KEY --country BGD
```

স্ক্রিপ্টটি স্বয়ংক্রিয়ভাবে ডেটা ডাউনলোড করে `raw_data/` ফোল্ডারে CSV হিসেবে সংরক্ষণ করবে।
