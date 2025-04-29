import os
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

def find_csv_files(directory):
    """ค้นหาไฟล์ CSV ในโฟลเดอร์ที่ระบุ"""
    csv_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and file.endswith(".csv"):
            csv_files.append(file_path)
    return csv_files

def process_csv_files(csv_files):
    """รวมข้อมูลจากไฟล์ CSV หลายไฟล์"""
    all_data = pd.DataFrame()
    for file in csv_files:
        df = pd.read_csv(file, on_bad_lines='skip')
        all_data = pd.concat([all_data, df], ignore_index=True)
    
    # แปลงคอลัมน์เวลาและเรียงข้อมูล
    all_data['timestamp'] = pd.to_datetime(all_data['timestamp'], format='mixed')
    all_data = all_data.sort_values(by='timestamp').reset_index(drop=True)
    return all_data

def parse_excel_file(excel_file_path):
    """อ่านไฟล์ Excel และแปลงข้อมูลวันเวลา"""
    try:
        index_df = pd.read_excel(excel_file_path, sheet_name="Report")
        
        # ตรวจสอบคอลัมน์ที่จำเป็น
        required_columns = ['Start date', 'End date', 'Time', 'room number', 'room name', 'Sensor start', 'Sensor stop']
        if not all(col in index_df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in index_df.columns]
            raise ValueError(f"Missing columns in Excel file: {missing_cols}")
        
        # แปลงวันเวลา
        index_df['start_time'] = pd.to_datetime(
            index_df['Start date'].astype(str) + ' ' + index_df['Time'].astype(str),
            errors='coerce'
        )
        index_df['end_time'] = pd.to_datetime(
            index_df['End date'].astype(str) + ' ' + index_df['Time'].astype(str),
            errors='coerce'
        )
        
        return index_df
    except Exception as e:
        raise Exception(f"Error parsing Excel file: {str(e)}")

def filter_data_by_time_and_sensors(all_data, start_time, end_time, start_sensor, end_sensor, additional_sensors=None, exclude_sensors=None):
    """กรองข้อมูลตามช่วงเวลาและเซ็นเซอร์ที่ระบุ"""
    # สร้างรายการเซ็นเซอร์
    sensor_lst = list(range(start_sensor, end_sensor + 1))
    
    # เพิ่มเซ็นเซอร์เพิ่มเติม (ถ้ามี)
    if additional_sensors:
        sensor_lst.extend(additional_sensors)
    
    # ลบเซ็นเซอร์ที่ไม่ต้องการ (ถ้ามี)
    if exclude_sensors:
        sensor_lst = [x for x in sensor_lst if x not in exclude_sensors]
    
    # สร้างชื่อคอลัมน์สำหรับเซ็นเซอร์
    sensor_columns_temp = [f"TempSensor{i}" for i in sensor_lst]
    sensor_columns_humidity = [f"RHSensor{i}" for i in sensor_lst]
    sensor_columns = sensor_columns_temp + sensor_columns_humidity
    
    # กรองข้อมูลตามช่วงเวลา
    filtered_data = all_data[
        (all_data['timestamp'] >= pd.to_datetime(start_time)) &
        (all_data['timestamp'] <= pd.to_datetime(end_time))
    ]
    
    # เลือกคอลัมน์ที่ต้องการ
    selected_columns = ['timestamp'] + [col for col in sensor_columns if col in filtered_data.columns]
    selected_data = filtered_data[selected_columns]
    
    return selected_data, sensor_columns_temp, sensor_columns_humidity

def check_data_loss(selected_data, start_sensor, limit_time=60, limit_percentage=0.3):
    """ตรวจสอบช่วงเวลาที่ข้อมูลขาดหาย"""
    results = []
    warnings = []
    
    for i in range(1, len(selected_data.columns)):
        sensor = selected_data.columns[i]
        sensor_num = int(sensor.replace("TempSensor", "").replace("RHSensor", ""))
        
        # ตรวจสอบเฉพาะคอลัมน์ TempSensor
        if not sensor.startswith("TempSensor"):
            continue
            
        # หาช่วงที่ข้อมูลเป็น 0
        test_df = selected_data.iloc[:, [0, i]][selected_data.iloc[:, i] == 0.0]
        test_df['timestamp'] = pd.to_datetime(test_df['timestamp'], errors='coerce')
        test_df = test_df.dropna(subset=['timestamp'])
        
        if len(test_df) == 0:
            results.append(f"Sensor {sensor_num}: No data loss detected.")
            continue
            
        # คำนวณช่วงเวลาที่ต่อเนื่องกัน
        test_df['time_diff'] = test_df['timestamp'].diff().dt.total_seconds()
        test_df['group'] = (test_df['time_diff'] > 120).cumsum()
        grouped = test_df.groupby('group')
        
        # ตรวจสอบแต่ละช่วง
        total_duration = 0
        for group_id, group in grouped:
            start = group['timestamp'].iloc[0]
            end = group['timestamp'].iloc[-1]
            duration_minutes = ((end - start).total_seconds() / 60) + 1
            total_duration += duration_minutes
            
            result_text = f"Sensor {sensor_num}: {start} to {end} -> Duration: {duration_minutes:.2f} minutes"
            results.append(result_text)
            
            if duration_minutes > limit_time:
                warning = f"⚠️ Warning: Sensor {sensor_num} has data loss exceeding {limit_time} minutes"
                warnings.append(warning)
        
        # ตรวจสอบรวม
        percentage = (total_duration / (7 * 24 * 60)) * 100
        results.append(f"Sensor {sensor_num}: Total Duration: {total_duration:.2f} minutes = {percentage:.4f}%")
        
        if percentage > limit_percentage * 100:
            warning = f"⚠️ Warning: Sensor {sensor_num} has total data loss exceeding {limit_percentage * 100}%"
            warnings.append(warning)
    
    return results, warnings

def vtn_imputation(df, temp_cols, humidity_cols, n_neighbors=4, reference_period=2):
    """
    Perform Virtual Temporal Neighbor (VTN) imputation on temperature and humidity sensor data.
    
    Parameters:
    df (DataFrame): Dataframe ที่มีข้อมูลเซ็นเซอร์
    temp_cols (list): รายชื่อคอลัมน์เซ็นเซอร์อุณหภูมิ
    humidity_cols (list): รายชื่อคอลัมน์เซ็นเซอร์ความชื้น
    n_neighbors (int): จำนวนเซ็นเซอร์ข้างเคียงที่จะใช้ในการคำนวณ
    reference_period (int): ช่วงเวลา (หน่วยชั่วโมง) สำหรับการเรียนรู้ความสัมพันธ์ระหว่างเซ็นเซอร์
    
    Returns:
    DataFrame: Dataframe ที่มีการเติมข้อมูลที่หายไป
    """
    # สร้างสำเนาเพื่อไม่ให้กระทบข้อมูลต้นฉบับ
    result_df = df.copy()
    
    # ประมวลผลคอลัมน์อุณหภูมิ
    _process_sensor_group(df, result_df, temp_cols, n_neighbors, reference_period)
    
    # ประมวลผลคอลัมน์ความชื้น
    _process_sensor_group(df, result_df, humidity_cols, n_neighbors, reference_period)
    
    return result_df

def _process_sensor_group(df, result_df, sensor_cols, n_neighbors, reference_period):
    """ประมวลผลกลุ่มเซ็นเซอร์ที่เกี่ยวข้องกัน (อุณหภูมิหรือความชื้น)"""
    # ประมวลผลแต่ละคอลัมน์เซ็นเซอร์
    for target_col in sensor_cols:
        # ข้ามหากคอลัมน์ไม่มีอยู่
        if target_col not in df.columns:
            continue
        
        # แปลงค่า 0 เป็น NaN สำหรับการประมวลผล
        missing_mask = (df[target_col] == 0) | df[target_col].isna()
        
        # ข้ามหากไม่มีค่าที่หายไป
        if not missing_mask.any():
            continue
        
        # หาเซ็นเซอร์ข้างเคียงที่เป็นไปได้ (ไม่รวมเซ็นเซอร์ปัจจุบัน)
        neighbor_cols = [col for col in sensor_cols if col != target_col and col in df.columns]
        
        # ดึงข้อมูลอ้างอิงที่มีค่าไม่หายสำหรับเซ็นเซอร์เป้าหมาย
        if 'timestamp' in df.columns and pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            # ใช้ข้อมูลจากช่วงอ้างอิงก่อนที่ข้อมูลจะเริ่มหาย
            latest_valid_time = df.loc[~missing_mask, 'timestamp'].max()
            if pd.notna(latest_valid_time):
                reference_start = latest_valid_time - pd.Timedelta(hours=reference_period)
                reference_data = df[(df['timestamp'] >= reference_start) & (~missing_mask)]
            else:
                reference_data = df[~missing_mask]
        else:
            # ใช้ข้อมูลที่มีทั้งหมดเป็นข้อมูลอ้างอิง
            reference_data = df[~missing_mask]
        
        # หากมีข้อมูลอ้างอิงไม่เพียงพอ ให้ใช้ interpolation แทน
        if len(reference_data) < 10:
            result_df.loc[missing_mask, target_col] = np.nan  # แปลง 0 เป็น NaN
            result_df.loc[:, target_col] = result_df[target_col].interpolate(method='linear')
            continue
        
        # เลือกเซ็นเซอร์ข้างเคียงที่ใกล้ที่สุดตามค่าสหสัมพันธ์
        top_neighbors = _select_nearest_neighbors(reference_data, target_col, neighbor_cols, n_neighbors)
        
        # หากไม่พบเซ็นเซอร์ข้างเคียงที่เหมาะสม ให้ใช้ interpolation แทน
        if not top_neighbors:
            result_df.loc[missing_mask, target_col] = np.nan
            result_df.loc[:, target_col] = result_df[target_col].interpolate(method='linear')
            continue
        
        # คำนวณความแตกต่างเฉลี่ย (deltas) ระหว่างเซ็นเซอร์เป้าหมายและแต่ละเซ็นเซอร์ข้างเคียง
        deltas = _calculate_sensor_deltas(reference_data, target_col, top_neighbors)
        
        # ใช้ VTN imputation กับค่าที่หายไป
        for idx in df.index[missing_mask]:
            # รับค่าปัจจุบันจากเซ็นเซอร์ข้างเคียง
            neighbor_readings = {}
            for neighbor in top_neighbors:
                val = df.loc[idx, neighbor]
                if pd.notna(val) and val != 0:
                    neighbor_readings[neighbor] = val
            
            # หากมีค่าจากเซ็นเซอร์ข้างเคียงอย่างน้อยหนึ่งตัว
            if neighbor_readings:
                # คำนวณค่าประมาณโดยใช้แต่ละเซ็นเซอร์ข้างเคียง
                estimates = []
                for neighbor, reading in neighbor_readings.items():
                    if neighbor in deltas:
                        estimates.append(reading + deltas[neighbor])
                
                # หาค่าเฉลี่ยของค่าประมาณหากมีค่าประมาณอย่างน้อยหนึ่งค่า
                if estimates:
                    result_df.loc[idx, target_col] = sum(estimates) / len(estimates)
                else:
                    result_df.loc[idx, target_col] = np.nan
            else:
                result_df.loc[idx, target_col] = np.nan
        
        # เติมค่า NaN ที่เหลือโดยใช้ interpolation
        if result_df[target_col].isna().any():
            result_df.loc[:, target_col] = result_df[target_col].interpolate(method='linear')

def _select_nearest_neighbors(reference_data, target_col, neighbor_cols, n_neighbors):
    """เลือกเซ็นเซอร์ข้างเคียงที่ใกล้ที่สุดตามค่าสหสัมพันธ์"""
    # คำนวณค่าสหสัมพันธ์ระหว่างเซ็นเซอร์เป้าหมายและแต่ละเซ็นเซอร์ที่อาจเป็นข้างเคียง
    correlations = {}
    for neighbor in neighbor_cols:
        # คำนวณสหสัมพันธ์เมื่อทั้งสองเซ็นเซอร์มีค่าที่ถูกต้อง
        if reference_data[target_col].notna().any() and reference_data[neighbor].notna().any():
            # กรองค่า 0 ในคอลัมน์ข้างเคียง
            valid_data = reference_data[(reference_data[target_col].notna()) & 
                                       (reference_data[neighbor].notna()) &
                                       (reference_data[neighbor] != 0)]
            if len(valid_data) >= 5:  # ต้องการจุดข้อมูลขั้นต่ำบางจำนวน
                corr = valid_data[target_col].corr(valid_data[neighbor])
                if pd.notna(corr):
                    correlations[neighbor] = abs(corr)  # ใช้ค่าสหสัมพันธ์สัมบูรณ์
    
    # เลือก n_neighbors ตัวที่มีค่าสหสัมพันธ์สูงสุด
    if correlations:
        top_neighbors = sorted(correlations.items(), key=lambda x: x[1], reverse=True)[:n_neighbors]
        return [col for col, _ in top_neighbors]
    
    # หากไม่สามารถคำนวณค่าสหสัมพันธ์ได้ ให้ลองใช้การเลือกตามตำแหน่ง
    # (สมมติว่าเซ็นเซอร์เรียงลำดับตามความใกล้ชิด)
    try:
        target_idx = int(''.join(filter(str.isdigit, target_col)))
        position_based = []
        for neighbor in neighbor_cols:
            try:
                neighbor_idx = int(''.join(filter(str.isdigit, neighbor)))
                position_based.append((neighbor, abs(neighbor_idx - target_idx)))
            except:
                continue
        
        if position_based:
            position_based.sort(key=lambda x: x[1])  # เรียงตามความใกล้ชิด
            return [col for col, _ in position_based[:n_neighbors]]
    except:
        pass
    
    # หากวิธีอื่นล้มเหลว เพียงแค่เลือก n_neighbors ตัวแรก
    return neighbor_cols[:min(n_neighbors, len(neighbor_cols))]

def _calculate_sensor_deltas(reference_data, target_col, neighbor_cols):
    """คำนวณ delta (ความแตกต่าง) เฉลี่ยระหว่างเซ็นเซอร์เป้าหมายและแต่ละเซ็นเซอร์ข้างเคียง"""
    deltas = {}
    
    for neighbor in neighbor_cols:
        # ใช้เฉพาะแถวที่ทั้งสองเซ็นเซอร์มีค่าที่ถูกต้อง
        valid_rows = reference_data[(reference_data[target_col].notna()) & 
                                   (reference_data[neighbor].notna()) &
                                   (reference_data[neighbor] != 0)]
        
        if len(valid_rows) >= 5:  # ต้องการจุดข้อมูลขั้นต่ำบางจำนวน
            # คำนวณความแตกต่างเฉลี่ย
            delta = (valid_rows[target_col] - valid_rows[neighbor]).mean()
            deltas[neighbor] = delta
    
    return deltas

@st.cache_data
def process_csv_files_cached(csv_files):
    """รวมข้อมูลจากไฟล์ CSV หลายไฟล์ พร้อมการ cache"""
    all_data = pd.DataFrame()
    for file in csv_files:
        df = pd.read_csv(file, on_bad_lines='skip')
        all_data = pd.concat([all_data, df], ignore_index=True)
    
    # แปลงคอลัมน์เวลาและเรียงข้อมูล
    all_data['timestamp'] = pd.to_datetime(all_data['timestamp'], format='mixed')
    all_data = all_data.sort_values(by='timestamp').reset_index(drop=True)
    return all_data

@st.cache_data
def parse_excel_file_cached(excel_file_path):
    """อ่านไฟล์ Excel และแปลงข้อมูลวันเวลา พร้อมการ cache"""
    try:
        index_df = pd.read_excel(excel_file_path, sheet_name="Report")
        
        # ตรวจสอบคอลัมน์ที่จำเป็น
        required_columns = ['Start date', 'End date', 'Time', 'room number', 'room name', 'Sensor start', 'Sensor stop']
        if not all(col in index_df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in index_df.columns]
            raise ValueError(f"Missing columns in Excel file: {missing_cols}")
        
        # แปลงวันเวลา
        index_df['start_time'] = pd.to_datetime(
            index_df['Start date'].astype(str) + ' ' + index_df['Time'].astype(str),
            errors='coerce'
        )
        index_df['end_time'] = pd.to_datetime(
            index_df['End date'].astype(str) + ' ' + index_df['Time'].astype(str),
            errors='coerce'
        )
        
        return index_df
    except Exception as e:
        raise Exception(f"Error parsing Excel file: {str(e)}")

def list_existing_files(directory, file_extension):
    """ดึงรายการไฟล์ที่มีอยู่ในระบบตามนามสกุลไฟล์ที่กำหนด"""
    files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.endswith(file_extension):
                files.append(os.path.join(directory, file))
    return files
