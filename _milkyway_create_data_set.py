from skyfield.api import load, Topos, Star
from skyfield import almanac
from datetime import datetime, timedelta
import pytz

# =================ตั้งค่าพิกัดและปีที่นี่=================
# พิกัดตัวอย่าง: ยอดดอยอินทนนท์ (เปลี่ยนเป็นที่ที่คุณต้องการ)
LATITUDE = 14.4390
LONGITUDE = 101.3725
YEAR = 2026

# ตั้งค่า Timezone เป็นประเทศไทย
TZ = pytz.timezone('Asia/Bangkok')

# มุมสูงขั้นต่ำของทางช้างเผือกที่จะเริ่มถ่าย (องศา)
MIN_MW_ALTITUDE = 10.0 
# ====================================================

def calculate_milkyway_window():
    print(f"กำลังคำนวณข้อมูลปี {YEAR} สำหรับพิกัด {LATITUDE}, {LONGITUDE}...")
    print("กรุณารอสักครู่ (อาจใช้เวลา 10-20 วินาที)...")

    # โหลดข้อมูลดาราศาสตร์
    # de421.bsp (17 MB): (แนะนำสำหรับมือใหม่/ทั่วไป) ครอบคลุมปี 1900-2050 ไฟล์เล็ก โหลดไว แม่นยำเพียงพอสำหรับการถ่ายภาพ
    # de440s.bsp (32 MB): (แนะนำสำหรับความแม่นยำยุคใหม่) เป็นมาตรฐานใหม่ของ NASA (ตั้งแต่ปี 2020) ครอบคลุมปี 1849-2150 แม่นยำกว่า de421 เล็กน้อย
    # de440.bsp (113 MB): ไฟล์เต็มของ de440 ครอบคลุมยาวนานมาก (ค.ศ. 1550-2650) ใช้สำหรับงานวิจัยประวัติศาสตร์หรืออนาคตไกลๆ
    # de422.bsp (623 MB): ไฟล์ยักษ์ ครอบคลุมยุคไดโนเสาร์ถึงอนาคต (3000 BC - 3000 AD) นานๆ จะมีคนใช้ทีครับ

    eph = load('de440s.bsp')
    sun = eph['sun']
    moon = eph['moon']
    earth = eph['earth']
    
    # กำหนดพิกัดสถานที่
    location = earth + Topos(latitude_degrees=LATITUDE, longitude_degrees=LONGITUDE)
    
    # กำหนดพิกัดใจกลางทางช้างเผือก (Galactic Center - Sagittarius A*)
    # RA: 17h 45m 40s | Dec: -29° 00' 28"
    galactic_center = Star(ra_hours=(17, 45, 40), dec_degrees=(-29, 0, 28))

    results = []
    
    # เริ่มลูปตั้งแต่วันที่ 1 ม.ค. ถึง 31 ธ.ค.
    start_date = datetime(YEAR, 1, 1, 12, 0, 0, tzinfo=TZ) # เริ่มเที่ยงวัน
    ts = load.timescale()

    for day in range(365):
        current_date = start_date + timedelta(days=day)
        
        # เราจะเช็คช่วงเวลาตั้งแต่ 18:00 (เย็น) ถึง 06:00 (เช้าวันถัดไป)
        # โดยเช็คทุกๆ 10 นาที เพื่อความรวดเร็ว
        check_start = current_date.replace(hour=18, minute=0, second=0)
        check_end = check_start + timedelta(hours=12)
        
        window_start = None
        window_end = None
        
        # สร้างช่วงเวลาเช็ค (Time step 10 นาที)
        time_steps = []
        temp_time = check_start
        while temp_time < check_end:
            time_steps.append(temp_time)
            temp_time += timedelta(minutes=10)

        # แปลงเวลาทั้งหมดเป็น Time Object ของ Skyfield ทีเดียว (เร็วกว่า loop)
        t_list = ts.from_datetimes(time_steps)
        
        # คำนวณตำแหน่งดวงดาวทั้งหมดทีเดียว (Vectorized operation)
        observer = location.at(t_list)
        
        # 1. เช็คดวงอาทิตย์ (ต้องมืดสนิท Alt < -18)
        sun_alt = observer.observe(sun).apparent().altaz()[0].degrees
        is_dark = sun_alt < -18

        # 2. เช็คทางช้างเผือก (ต้องสูงกว่ากำหนด)
        mw_alt = observer.observe(galactic_center).apparent().altaz()[0].degrees
        is_mw_up = mw_alt > MIN_MW_ALTITUDE

        # 3. เช็คดวงจันทร์ (ต้องอยู่ต่ำกว่าขอบฟ้า หรือ เฟสบางมากๆ)
        moon_app = observer.observe(moon).apparent()
        moon_alt = moon_app.altaz()[0].degrees
        # คำนวณเฟสของดวงจันทร์ (0.0 - 1.0)
        moon_phase = almanac.fraction_illuminated(eph, 'moon', t_list)
        
        # เงื่อนไข: ดวงจันทร์ตก (Alt < 0) หรือ สว่างน้อยกว่า 20%
        is_moon_ok = (moon_alt < 0) | (moon_phase < 0.2)

        # รวมเงื่อนไข: มืด + ทางช้างเผือกขึ้น + ไม่มีดวงจันทร์กวน
        visible_mask = is_dark & is_mw_up & is_moon_ok

        # หาช่วงเวลา Start - End ของคืนนั้น
        valid_indices = [i for i, x in enumerate(visible_mask) if x]

        if valid_indices:
            # มีช่วงเวลาที่ถ่ายได้
            first_idx = valid_indices[0]
            last_idx = valid_indices[-1]
            
            # ดึงเวลา
            s_time = time_steps[first_idx]
            e_time = time_steps[last_idx]
            
            # ถ้าช่วงเวลาน้อยกว่า 20 นาที ไม่นับ (ถ่ายไม่ทัน)
            if (e_time - s_time).total_seconds() > 1200:
                # Format วันที่และเวลาตามโจทย์
                # หมายเหตุ: Date ใช้เป็นวันที่เริ่มดู (เย็น) แม้จบเช้ามืดอีกวัน
                date_str = s_time.strftime("%Y-%m-%d")
                start_str = s_time.strftime("%H:%M")
                end_str = e_time.strftime("%H:%M")
                
                results.append(f'    {{"Date": "{date_str}", "Start": "{start_str}", "End": "{end_str}"}},')

    # พิมพ์ผลลัพธ์
    print("\ndata = [")
    for line in results:
        print(line)
    print("]")

if __name__ == "__main__":
    calculate_milkyway_window()