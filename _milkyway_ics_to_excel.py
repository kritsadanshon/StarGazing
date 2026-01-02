import icalendar
import pandas as pd
import re
from datetime import datetime
import pytz

def ics_to_excel(ics_file_path, output_excel_path):
    # 1. เปิดและอ่านไฟล์ ICS
    try:
        with open(ics_file_path, 'rb') as f:
            cal = icalendar.Calendar.from_ical(f.read())
    except FileNotFoundError:
        print(f"Error: ไม่พบไฟล์ {ics_file_path}")
        return

    data_list = []
    
    # กำหนด Timezone เป็นประเทศไทย (Asia/Bangkok)
    thai_tz = pytz.timezone('Asia/Bangkok')

    # 2. วนลูปอ่านข้อมูลแต่ละ Event
    for component in cal.walk():
        if component.name == "VEVENT":
            event_data = {}
            
            # --- ดึงข้อมูลเวลา (DTSTART) ---
            # ตรวจสอบว่ามี DTSTART หรือไม่
            dtstart_prop = component.get('DTSTART')
            if dtstart_prop is None:
                continue # ข้ามถ้าไม่มีเวลาเริ่ม
            
            dtstart = dtstart_prop.dt

            # แปลงเวลาเริ่มเป็น Timezone ไทย
            if isinstance(dtstart, datetime):
                if dtstart.tzinfo is None:
                    dtstart = pytz.utc.localize(dtstart)
                dtstart = dtstart.astimezone(thai_tz)
                event_data['Start Time'] = dtstart.strftime('%Y-%m-%d %H:%M:%S')
                event_data['Date'] = dtstart.strftime('%Y-%m-%d')
                event_data['Time Start'] = dtstart.strftime('%H:%M')
            else:
                # กรณีเป็น Date object (ทั้งวัน)
                event_data['Start Time'] = str(dtstart)
                event_data['Date'] = str(dtstart)
                event_data['Time Start'] = "All Day"

            # --- ดึงข้อมูลเวลาสิ้นสุด (DTEND) ---
            # แก้ไข: ตรวจสอบก่อนว่ามี DTEND หรือไม่ ป้องกัน Error 'NoneType'
            dtend_prop = component.get('DTEND')
            if dtend_prop:
                dtend = dtend_prop.dt
                if isinstance(dtend, datetime):
                    if dtend.tzinfo is None:
                        dtend = pytz.utc.localize(dtend)
                    dtend = dtend.astimezone(thai_tz)
                    event_data['End Time'] = dtend.strftime('%Y-%m-%d %H:%M:%S')
                    event_data['Time End'] = dtend.strftime('%H:%M')

                    # คำนวณระยะเวลา (Duration) เฉพาะเมื่อมีทั้ง Start และ End และเป็น datetime
                    if isinstance(dtstart, datetime):
                        duration = (dtend - dtstart).total_seconds() / 60
                        event_data['Duration (Minutes)'] = int(duration)
                else:
                     # กรณี End เป็น Date (ทั้งวัน)
                    event_data['End Time'] = str(dtend)
                    event_data['Time End'] = ""
                    event_data['Duration (Minutes)'] = 0
            else:
                # กรณีไม่มีเวลาสิ้นสุด
                event_data['End Time'] = ""
                event_data['Time End'] = ""
                event_data['Duration (Minutes)'] = 0

            # --- ดึงหัวข้อ (SUMMARY) ---
            summary = component.get('SUMMARY')
            event_data['Event Name'] = str(summary) if summary else ""

            # --- ดึงและแยกข้อมูลจากคำอธิบาย (DESCRIPTION) ---
            description = component.get('DESCRIPTION')
            desc_text = str(description) if description else ""
            event_data['Raw Description'] = desc_text

            # ใช้ Regular Expression (Regex) เพื่อดึงค่าตัวเลขออกมา
            lat_match = re.search(r'Lat\s*([\d\.]+)', desc_text)
            lon_match = re.search(r'Lon\s*([\d\.]+)', desc_text)
            max_alt_match = re.search(r'MaxAlt\s*~?(\d+)', desc_text)

            event_data['Latitude'] = float(lat_match.group(1)) if lat_match else None
            event_data['Longitude'] = float(lon_match.group(1)) if lon_match else None
            event_data['Max Altitude (deg)'] = int(max_alt_match.group(1)) if max_alt_match else None

            data_list.append(event_data)

    # 3. สร้าง DataFrame และส่งออกเป็น Excel
    if data_list:
        df = pd.DataFrame(data_list)
        
        # เรียงลำดับตามเวลาเริ่ม (ถ้ามีคอลัมน์ Start Time)
        if 'Start Time' in df.columns:
            df = df.sort_values(by='Start Time')
        
        # จัดลำดับคอลัมน์ใหม่
        columns_order = [
            'Date', 'Time Start', 'Time End', 'Duration (Minutes)', 
            'Max Altitude (deg)', 'Event Name', 'Latitude', 'Longitude', 'Raw Description'
        ]
        existing_cols = [col for col in columns_order if col in df.columns]
        df = df[existing_cols]

        df.to_excel(output_excel_path, index=False)
        print(f"สร้างไฟล์ Excel สำเร็จ: {output_excel_path}")
        print(f"จำนวนรายการทั้งหมด: {len(df)}")
    else:
        print("ไม่พบข้อมูล Event ในไฟล์ ICS")

# --- เรียกใช้งานฟังก์ชัน ---
input_filename = 'StarGazing.ics' 
output_filename = 'StarGazing_Schedule.xlsx'

ics_to_excel(input_filename, output_filename)