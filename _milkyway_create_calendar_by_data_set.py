import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.image as mpimg
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# --- 1. ตั้งค่าชื่อไฟล์รูปภาพพื้นหลัง ---
bg_image_path = 'background_.jpg' # เปลี่ยนเป็นชื่อไฟล์ของคุณ

# --- 2. ข้อมูล (Data) ---
data = [
    {"Date": "2026-10-01", "Start": "19:00", "End": "21:10"},
    {"Date": "2026-10-02", "Start": "19:00", "End": "21:10"},
    {"Date": "2026-10-03", "Start": "19:00", "End": "21:00"},
    {"Date": "2026-10-04", "Start": "19:00", "End": "21:00"},
    {"Date": "2026-10-05", "Start": "19:00", "End": "21:00"},
    {"Date": "2026-10-06", "Start": "19:00", "End": "20:50"},
    {"Date": "2026-10-07", "Start": "19:00", "End": "20:50"},
    {"Date": "2026-10-08", "Start": "19:00", "End": "20:40"},
    {"Date": "2026-10-09", "Start": "19:00", "End": "20:40"},
    {"Date": "2026-10-10", "Start": "19:00", "End": "20:40"},
    {"Date": "2026-10-11", "Start": "19:00", "End": "20:30"},
    {"Date": "2026-10-12", "Start": "18:50", "End": "20:30"},
    {"Date": "2026-10-13", "Start": "18:50", "End": "20:20"},
    {"Date": "2026-10-14", "Start": "18:50", "End": "20:20"},
    {"Date": "2026-10-28", "Start": "18:50", "End": "19:20"},
    {"Date": "2026-10-29", "Start": "18:50", "End": "19:20"},
    {"Date": "2026-10-30", "Start": "18:50", "End": "19:20"}
]

# --- 3. เตรียมข้อมูล ---
df = pd.DataFrame(data)

def time_to_plot_val(t_str):
    h, m = map(int, t_str.split(':'))
    val = h + m/60
    if val < 12: # ถ้าหลังเที่ยงคืน ให้บวก 24 เพื่อให้กราฟต่อเนื่องไปทางขวา
        val += 24
    return val

def get_night_date(row):
    date_obj = pd.to_datetime(row['Date'])
    h, _ = map(int, row['Start'].split(':'))
    if h < 12: # เช้ามืด ให้นับเป็นคืนก่อนหน้า
        return date_obj - timedelta(days=1)
    return date_obj

df['Start_Val'] = df['Start'].apply(time_to_plot_val)
df['End_Val'] = df['End'].apply(time_to_plot_val)
df['Duration'] = df['End_Val'] - df['Start_Val']
df['Night_Date'] = df.apply(get_night_date, axis=1)

# เรียงลำดับข้อมูลตามวันที่
df = df.sort_values(by='Night_Date').reset_index(drop=True)

# --- 4. สร้างกราฟ ---
plt.style.use('dark_background')

# คำนวณความสูงรูปกราฟ (High Resolution Height)
row_height = 0.4 # ความสูงต่อ 1 แถวข้อมูล (นิ้ว)
fig_height = max(8, len(df) * row_height) 
fig, ax = plt.subplots(figsize=(15, fig_height))

# ** หัวใจสำคัญ: ใช้ index (0, 1, 2...) เป็นแกน Y แทนวันที่จริง **
# เพื่อให้กราฟเรียงติดกันโดยไม่มีช่องว่างของวันที่หายไป
y_positions = np.arange(len(df))

# วาดกราฟแท่ง
bars = ax.barh(y_positions, df['Duration'], left=df['Start_Val'], 
               color='#FFCC80', edgecolor='white', height=0.6, alpha=0.9, zorder=3)

# ใส่ข้อความกำกับเวลาท้ายแท่ง
for i, bar in enumerate(bars):
    duration_mins = int(round(df['Duration'].iloc[i] * 60))
    # ปรับตำแหน่งข้อความ
    x_pos = bar.get_x() + bar.get_width() + 0.1
    y_pos = bar.get_y() + bar.get_height()/2
    ax.text(x_pos, y_pos, f"{duration_mins} mins", va='center', color='white', fontsize=10, zorder=4)

# --- 5. ตั้งค่าแกน ---
# แกน X: เวลา
ax.set_xlim(18, 30.5)
x_ticks = [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
x_labels = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00']
ax.set_xticks(x_ticks)
ax.set_xticklabels(x_labels, fontsize=12, fontweight='bold', color='white')
ax.set_xlabel('Milkyway', fontsize=14, color='#FFD700', labelpad=10)
ax.xaxis.tick_top()
ax.xaxis.set_label_position('top')

# แกน Y: แสดงวันที่ (Map จาก index กลับเป็นชื่อวัน)
date_labels = [d.strftime('%d %b') for d in df['Night_Date']]
ax.set_yticks(y_positions)
ax.set_yticklabels(date_labels, fontsize=11, color='#DDDDDD')
ax.set_ylim(-0.5, len(df) - 0.5)
ax.invert_yaxis() # เรียงจากบนลงล่าง

# ขีดเส้นแบ่งระหว่างเดือน (Optional: เพื่อให้ดูง่ายขึ้นเมื่อวันที่กระโดด)
for i in range(len(df) - 1):
    curr_month = df['Night_Date'].iloc[i].month
    next_month = df['Night_Date'].iloc[i+1].month
    if curr_month != next_month:
        # วาดเส้นคั่นเมื่อเปลี่ยนเดือน
        ax.axhline(y=i + 0.5, color='white', linestyle='--', alpha=0.5, linewidth=1, zorder=2)

# เส้น Grid แนวตั้ง
ax.grid(axis='x', linestyle='--', alpha=0.3, color='white', zorder=1)
ax.axvline(x=24, color='#00BFFF', linestyle='-', alpha=0.8, linewidth=2, zorder=2)

# --- 6. ใส่รูปภาพพื้นหลัง ---
try:
    img = mpimg.imread(bg_image_path)
    # Extent ต้องปรับตามแกน Y ใหม่ (0 ถึง len(df))
    # y_min = len(df) - 0.5 (ล่างสุด เพราะ invert), y_max = -0.5 (บนสุด)
    ax.imshow(img, extent=[18, 30.5, len(df)-0.5, -0.5], aspect='auto', zorder=0, alpha=0.5)
except FileNotFoundError:
    print(f"Warning: Image file '{bg_image_path}' not found. Using dark background.")
    ax.set_facecolor("#1a1a2e")

plt.tight_layout()
output_file = 'milkyway_.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"Graph saved to {output_file}")
plt.show()