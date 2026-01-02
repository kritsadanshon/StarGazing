from skyfield.api import load, Topos
from skyfield.data import mpc
from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2
import pandas as pd
import math
import json
import os
from datetime import datetime, timedelta
import pytz
import numpy as np

# ================= ⚙️ ตั้งค่าการค้นหา =================
SEARCH_YEAR = 2026          # ปีที่ต้องการค้นหา
START_MONTH = 1             # เดือนเริ่มต้น (เช่น ม.ค.)
END_MONTH = 1                # เดือนสิ้นสุด (เช่น ธ.ค.)
MAX_MAGNITUDE = 12.0        # ความสว่างขั้นต่ำ (แนะนำ 12 สำหรับถ่ายรูป, 6 สำหรับตาเปล่า)
LATITUDE = 18.5558          # ดอยอินทนนท์
LONGITUDE = 98.4822
THAI_TZ = pytz.timezone('Asia/Bangkok')

# มุมสูงขั้นต่ำของดาวหางที่จะเริ่มถ่าย (องศา)
MIN_MW_ALTITUDE = 15.0 

# --- ตั้งค่า Output ---
SAVE_JSON = True
JSON_FILENAME = f"comets_{SEARCH_YEAR}_month_{START_MONTH:02d}-{END_MONTH:02d}.json"
# ====================================================

def calculate_comet_magnitude(row, earth_dist, sun_dist):
    try:
        m1 = row.get('magnitude_g', row.get('magnitude_m1', row.get('M1', None)))
        if pd.isna(m1): return 999
        k = row.get('magnitude_k', row.get('K', 10.0))
        if pd.isna(k): k = 10.0
        mag = m1 + 5 * math.log10(earth_dist) + k * math.log10(sun_dist)
        return mag
    except:
        return 999

def get_closest_approach_in_year(comet, sun, earth, ts, year):
    # คำนวณ Perigee ครั้งเดียวตลอดทั้งปี
    days = range(1, 367) 
    times = ts.utc(year, 1, days)
    earth_at_times = earth.at(times)
    comet_at_times = earth_at_times.observe(comet)
    distances = comet_at_times.distance().au
    min_idx = np.argmin(distances)
    best_time_thai = times[min_idx].utc_datetime().replace(tzinfo=pytz.utc).astimezone(THAI_TZ)
    return best_time_thai, distances[min_idx]

def find_comets_multi_month():
    print(f"🚀 เริ่มภารกิจค้นหาดาวหาง ปี {SEARCH_YEAR} (เดือน {START_MONTH} - {END_MONTH})")
    
    # 1. โหลดข้อมูลครั้งเดียวใช้ยาวๆ
    url = 'https://www.minorplanetcenter.net/iau/MPCORB/CometEls.txt'
    print("📥 กำลังดาวน์โหลดข้อมูลล่าสุดจาก MPC (Force Reload)...")
    print("   (ขั้นตอนนี้ต้องต่อเน็ต และอาจใช้เวลาสักครู่)")
    with load.open(url, reload=True) as f:
        comets = mpc.load_comets_dataframe(f)
    if 'designation' not in comets.columns:
        comets = comets.reset_index()

    ts = load.timescale()
    sun = load('de421.bsp')['sun']
    earth = load('de421.bsp')['earth']
    location = earth + Topos(latitude_degrees=LATITUDE, longitude_degrees=LONGITUDE)

    all_results = [] # เก็บผลรวมทุกเดือน

    # 2. เริ่ม Loop ทีละเดือน
    for current_month in range(START_MONTH, END_MONTH + 1):
        print(f"\n🗓️  กำลังตรวจสอบเดือน {current_month}/{SEARCH_YEAR}...")
        
        # Screening วันที่ 15 ของเดือน
        try:
            mid_month_time = ts.utc(SEARCH_YEAR, current_month, 15)
        except ValueError:
            continue # ข้ามถ้าวันที่ผิดพลาด

        candidates = []
        for i, (index, row) in enumerate(comets.iterrows()):
            try:
                comet_orbit = sun + mpc.comet_orbit(row, ts, GM_SUN_Pitjeva_2005_km3_s2)
                pos_sun = sun.at(mid_month_time).observe(comet_orbit)
                pos_earth = earth.at(mid_month_time).observe(comet_orbit)
                mag = calculate_comet_magnitude(row, pos_earth.distance().au, pos_sun.distance().au)
                
                if mag <= MAX_MAGNITUDE:
                    candidates.append((row, mag))
            except:
                continue
        
        if not candidates:
            print(f"   - ไม่พบดาวหางเข้าเกณฑ์ในเดือนนี้")
            continue

        print(f"   - พบ {len(candidates)} ดวงที่มีลุ้น ตรวจสอบมุมมอง...")

        # Detailed Check (หัวค่ำ/เช้ามืด)
        check_times = [
            (ts.utc(SEARCH_YEAR, current_month, 15, 13, 0, 0), "หัวค่ำ (20:00 น.)"),
            (ts.utc(SEARCH_YEAR, current_month, 15, 21, 0, 0), "เช้ามืด (04:00 น.)")
        ]

        monthly_found = 0
        for row, est_mag in candidates:
            comet = sun + mpc.comet_orbit(row, ts, GM_SUN_Pitjeva_2005_km3_s2)
            visible = False
            best_alt = -90
            best_az = 0
            visible_period = ""
            check_time_str = ""
            
            for t, period_name in check_times:
                sun_alt = location.at(t).observe(sun).apparent().altaz()[0].degrees
                if sun_alt > -12: continue 
                
                alt, az, _ = location.at(t).observe(comet).apparent().altaz()
                
                if alt.degrees > MIN_MW_ALTITUDE: 
                    visible = True
                    if alt.degrees > best_alt: 
                        best_alt = alt.degrees
                        best_az = az.degrees
                        visible_period = period_name
                        dt_thai = t.utc_datetime().replace(tzinfo=pytz.utc).astimezone(THAI_TZ)
                        check_time_str = dt_thai.strftime("%Y-%m-%d %H:%M:%S")
            
            if visible:
                closest_date, closest_dist = get_closest_approach_in_year(comet, sun, earth, ts, SEARCH_YEAR)
                
                comet_info = {
                    "month": current_month, # ระบุเดือนที่เจอ
                    "year": SEARCH_YEAR,
                    "name": row['designation'],
                    "magnitude": round(est_mag, 2),
                    "altitude_max": round(best_alt, 2),
                    "azimuth": round(best_az, 2),
                    "visibility_period": visible_period,
                    "check_date_local": check_time_str,
                    "closest_approach": {
                        "date": closest_date.strftime("%Y-%m-%d"),
                        "distance_au": round(closest_dist, 4)
                    }
                }
                all_results.append(comet_info)
                monthly_found += 1
        
        print(f"   ✅ ยืนยันถ่ายได้: {monthly_found} ดวง")

    # 3. สรุปผลและ Save
    print("\n" + "="*70)
    print(f"🏁 สรุปผลการค้นหา {SEARCH_YEAR} (เดือน {START_MONTH}-{END_MONTH})")
    print("="*70)
    
    if not all_results:
        print("❌ ไม่พบดาวหางที่ถ่ายได้ตลอดช่วงเวลานี้")
    else:
        # เรียงตามเดือน แล้วตามความสว่าง
        all_results.sort(key=lambda x: (x['month'], x['magnitude']))
        
        for res in all_results:
            print(f"📅 เดือน {res['month']}: {res['name']}")
            print(f"    Mag: {res['magnitude']} | Alt: {res['altitude_max']}° | {res['visibility_period']}")
            print(f"    (ใกล้โลกสุด: {res['closest_approach']['date']} @ {res['closest_approach']['distance_au']} AU)")
            print("-" * 30)

    if SAVE_JSON and all_results:
        try:
            with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=4, ensure_ascii=False)
            print(f"\n💾 บันทึก JSON รวมสำเร็จ: {os.path.abspath(JSON_FILENAME)}")
        except Exception as e:
            print(f"\n⚠️ Error Saving JSON: {e}")

if __name__ == "__main__":
    find_comets_multi_month()