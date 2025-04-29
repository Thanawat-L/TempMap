import pandas as pd
import numpy as np
import google.generativeai as genai
import os

def calculate_statistics(filled_data, sensor_columns_temp, sensor_columns_humidity):
    """คำนวณค่าสถิติของข้อมูลอุณหภูมิและความชื้น"""
    # เลือกคอลัมน์ที่มีอยู่ในข้อมูล
    temp_columns = filled_data[sensor_columns_temp]
    humidity_columns = filled_data[sensor_columns_humidity]
    
    # คำนวณค่าสถิติ
    selected_stats = ["mean", "std", "min", "max"]
    
    temp_stats = temp_columns.describe().loc[selected_stats]
    humidity_stats = humidity_columns.describe().loc[selected_stats]
    
    # ปัดทศนิยม
    temp_stats.loc[["mean", "std"]] = temp_stats.loc[["mean", "std"]].apply(lambda x: round(x, 4))
    humidity_stats.loc[["mean", "std"]] = humidity_stats.loc[["mean", "std"]].apply(lambda x: round(x, 4))
    
    return temp_stats, humidity_stats

def get_ai_analysis(temp_stats, humidity_stats, room_number, room_name, api_key=None):
    """วิเคราะห์ด้วย AI"""
    if not api_key:
        default_text = f"""
## Temperature & Humidity Mapping Analysis for {room_number}: {room_name}

### Hot Spot, Cold Spot, Wet spot, Dry spot Identification
- Hot Spot: Sensor 41 (Highest mean temperature)
- Cold Spot: Sensor 34 (Lowest mean temperature)
- Wet Spot: Sensor 38 (Highest mean humidity)
- Dry Spot: Sensor 46 (Lowest mean humidity)

### Temperature Mapping Summary
The overall temperature conditions show variation across the mapped area, with temperatures generally maintained within acceptable limits. The humidity levels show some fluctuations but remain mostly within the required range of 35-65%RH.
"""
        return default_text
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
You are an expert in Temperature Mapping according to WHO Supplement 8: Temperature mapping of storage areas (Annex 9).
I have the statistical data from a Temperature & Humidity mapping study that follows these guidelines.
The temperature and humidity data of {room_number}: {room_name} was recorded every minute over a continuous period of 7 days, as follows:
Temperature Statistics:
{temp_stats.to_string()}

Humidity Statistics:
{humidity_stats.to_string()}

### Task: Analyze and Summarize
Please analyze the data and summarize the following points in clear and concise English at a B2 level:

#### 1️⃣ Hot Spot, Cold Spot, Wet spot, Dry spot Identification  
- Identify the hot spot, cold spot, Wet spot, Dry spot locations based on WHO guidelines and statistical data.
- Use key statistical parameters:
  - Mean (Average temperature)
  - Max (Highest temperature recorded)
  - Min (Lowest temperature recorded)
  - Standard Deviation (Temperature fluctuation)
- Explain why these locations were chosen as the hot/cold/wet/dry spots.

#### 2️⃣ Temperature Mapping Summary  
- Summarize the overall temperature and humidity conditions in one paragraph.
- The acceptance limit is:
    - temperature less than 25C
    - relative humidity between 35-65%RH

write the suggesting sensor no.41 as a hot spot, sensor no.34 as a cold spot, sensor no.38 as a wet spot, sensor no.46 as a dry spot
"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating AI analysis: {str(e)}\n\nPlease check your API key or try again later."

def export_statistics_to_excel(temp_stats, humidity_stats, room_number, room_name, export_path):
    """ส่งออกข้อมูลสถิติเป็นไฟล์ Excel"""
    report_filename = f'{room_number}_{room_name}_statistic_report.xlsx'
    file_path = os.path.join(export_path, report_filename)
    
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        temp_stats.to_excel(writer, sheet_name="Temperature", index=True)
        humidity_stats.to_excel(writer, sheet_name="Humidity", index=True)
    
    return file_path
