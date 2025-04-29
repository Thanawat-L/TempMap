import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime
import time
import base64
from io import BytesIO

# Import functions from utility modules
from utils.data_processor import (
    find_csv_files, process_csv_files, parse_excel_file, 
    filter_data_by_time_and_sensors, check_data_loss, vtn_imputation,
    process_csv_files_cached, parse_excel_file_cached, list_existing_files  # เพิ่มฟังก์ชันใหม่
)
from utils.visualization import create_temperature_chart, create_humidity_chart
from utils.analysis import calculate_statistics, get_ai_analysis, export_statistics_to_excel

# Set page configuration
st.set_page_config(
    page_title="Temperature & Humidity Mapping Analysis",
    page_icon="🌡️",
    layout="wide"
)

# Function to create download links
def get_excel_download_link(file_path, link_text):
    with open(file_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{os.path.basename(file_path)}">{link_text}</a>'
    return href

def get_csv_download_link(df, filename, link_text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

# Create necessary directories if they don't exist
os.makedirs("data/csv", exist_ok=True)
os.makedirs("data/excel", exist_ok=True)
os.makedirs("data/reports", exist_ok=True)
os.makedirs("data/temp", exist_ok=True)

# App title and introduction
st.title("🌡️ Temperature & Humidity Mapping Analysis")
st.markdown("""
This application helps you analyze temperature and humidity mapping data.
Upload your CSV data files and Temperature Mapping Plan to visualize and analyze the results.
""")

# Initialize session state variables if they don't exist
if 'csv_files_uploaded' not in st.session_state:
    st.session_state.csv_files_uploaded = False
if 'excel_file_uploaded' not in st.session_state:
    st.session_state.excel_file_uploaded = False
if 'all_data' not in st.session_state:
    st.session_state.all_data = None
if 'index_df' not in st.session_state:
    st.session_state.index_df = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'export_path' not in st.session_state:
    st.session_state.export_path = None

# Create tabs for different parts of the application
tab1, tab2, tab3 = st.tabs(["📂 Data Upload", "📊 Analysis", "📝 Results"])

# Tab 1: Data Upload
with tab1:
    st.header("Upload Data Files")
    
    # ตรวจสอบไฟล์ที่มีอยู่ในระบบ
    existing_csv_files = list_existing_files("data/csv", ".csv")
    existing_excel_files = list_existing_files("data/excel", ".xlsx")
    
    # เพิ่ม checkbox สำหรับเลือกใช้ไฟล์ที่มีอยู่หรืออัปโหลดใหม่
    use_existing_files = st.checkbox("ใช้ไฟล์ที่มีอยู่ในระบบ", value=bool(existing_csv_files and existing_excel_files))
    
    if use_existing_files and (existing_csv_files or existing_excel_files):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("ไฟล์ CSV ที่มีอยู่")
            if existing_csv_files:
                # เลือกไฟล์ที่มีอยู่แล้ว
                selected_csv_files = st.multiselect(
                    "เลือกไฟล์ CSV ที่ต้องการใช้", 
                    options=existing_csv_files,
                    default=existing_csv_files,
                    format_func=lambda x: os.path.basename(x)
                )
                
                if selected_csv_files:
                    with st.spinner("กำลังประมวลผลไฟล์ CSV..."):
                        st.session_state.all_data = process_csv_files_cached(selected_csv_files)
                        st.session_state.csv_files_uploaded = True
                    st.success(f"✅ ประมวลผล {len(selected_csv_files)} ไฟล์ CSV ที่มี {len(st.session_state.all_data)} จุดข้อมูล")
            else:
                st.info("ไม่พบไฟล์ CSV ในระบบ กรุณาอัปโหลดไฟล์ใหม่")
        
        with col2:
            st.subheader("ไฟล์ Excel ที่มีอยู่")
            if existing_excel_files:
                selected_excel = st.selectbox(
                    "เลือกไฟล์ Excel ที่ต้องการใช้", 
                    options=existing_excel_files,
                    format_func=lambda x: os.path.basename(x)
                )
                
                if selected_excel:
                    with st.spinner("กำลังประมวลผลไฟล์ Excel..."):
                        try:
                            st.session_state.index_df = parse_excel_file_cached(selected_excel)
                            st.session_state.excel_file_uploaded = True
                            st.success(f"✅ ประมวลผลไฟล์ Excel เรียบร้อยแล้ว มี {len(st.session_state.index_df)} รายการแมพปิ้ง")
                            
                            # แสดงตัวอย่างข้อมูล Excel
                            with st.expander("ดูข้อมูลแผนแมพปิ้ง"):
                                st.dataframe(st.session_state.index_df[['room number', 'room name', 'start_time', 'end_time', 'Sensor start', 'Sensor stop']])
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์ Excel: {str(e)}")
            else:
                st.info("ไม่พบไฟล์ Excel ในระบบ กรุณาอัปโหลดไฟล์ใหม่")
    
    # แสดงส่วนอัปโหลดไฟล์ใหม่
    if not use_existing_files or not (existing_csv_files and existing_excel_files):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("อัปโหลดไฟล์ข้อมูล CSV")
            uploaded_csv_files = st.file_uploader("อัปโหลดไฟล์ CSV หนึ่งไฟล์หรือมากกว่า", type="csv", accept_multiple_files=True)
            
            if uploaded_csv_files:
                # บันทึกไฟล์ CSV ที่อัปโหลด
                for uploaded_file in uploaded_csv_files:
                    file_path = os.path.join("data/csv", uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                st.success(f"✅ อัปโหลด {len(uploaded_csv_files)} ไฟล์ CSV สำเร็จ!")
                
                # ค้นหาและประมวลผลไฟล์ CSV ทั้งหมด
                csv_files = find_csv_files("data/csv")
                if csv_files:
                    with st.spinner("กำลังประมวลผลไฟล์ CSV..."):
                        st.session_state.all_data = process_csv_files_cached(csv_files)
                        st.session_state.csv_files_uploaded = True
                    st.success(f"✅ ประมวลผล {len(csv_files)} ไฟล์ CSV ที่มี {len(st.session_state.all_data)} จุดข้อมูล")
        
        with col2:
            st.subheader("อัปโหลดแผนแมพปิ้งอุณหภูมิ")
            uploaded_excel = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx", "xls"])
            
            if uploaded_excel:
                # บันทึกไฟล์ Excel ที่อัปโหลด
                excel_path = os.path.join("data/excel", uploaded_excel.name)
                with open(excel_path, "wb") as f:
                    f.write(uploaded_excel.getbuffer())
                
                st.success("✅ อัปโหลดไฟล์ Excel สำเร็จ!")
                
                # ประมวลผลไฟล์ Excel
                with st.spinner("กำลังประมวลผลไฟล์ Excel..."):
                    try:
                        st.session_state.index_df = parse_excel_file_cached(excel_path)
                        st.session_state.excel_file_uploaded = True
                        st.success(f"✅ ประมวลผลไฟล์ Excel เรียบร้อยแล้ว มี {len(st.session_state.index_df)} รายการแมพปิ้ง")
                        
                        # แสดงตัวอย่างข้อมูล Excel
                        with st.expander("ดูข้อมูลแผนแมพปิ้ง"):
                            st.dataframe(st.session_state.index_df[['room number', 'room name', 'start_time', 'end_time', 'Sensor start', 'Sensor stop']])
                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์ Excel: {str(e)}")

# Tab 2: Analysis
with tab2:
    st.header("Analyze Data")
    
    if not st.session_state.csv_files_uploaded or not st.session_state.excel_file_uploaded:
        st.warning("⚠️ Please upload both CSV and Excel files in the Data Upload tab first.")
    else:
        # Display selection for analysis
        st.subheader("Select Room to Analyze")
        
        # Create options from index_df
        options = []
        for idx, row in st.session_state.index_df.iterrows():
            if pd.notna(row['room number']) and pd.notna(row['room name']):
                options.append(f"{idx}: {row['room number']} - {row['room name']}")
        
        if options:
            selected_option = st.selectbox("Select room for analysis:", options)
            selected_idx = int(selected_option.split(":")[0])
            
            # Extract data for selected index
            row = st.session_state.index_df.loc[selected_idx]
            start_time = row['start_time']
            end_time = row['end_time']
            start_sensor = int(row['Sensor start'])
            end_sensor = int(row['Sensor stop'])
            room_number = row['room number']
            room_name = row['room name']
            
            st.info(f"Selected: {room_number}: {room_name} (Sensors {start_sensor}-{end_sensor}, {start_time} to {end_time})")
            
            # Optional settings for additional sensors
            with st.expander("Advanced Sensor Settings"):
                col1, col2 = st.columns(2)
                with col1:
                    additional_sensors_str = st.text_input("Add sensors (comma-separated numbers):", "")
                    additional_sensors = []
                    if additional_sensors_str:
                        try:
                            additional_sensors = [int(x.strip()) for x in additional_sensors_str.split(",")]
                        except:
                            st.error("Invalid format for additional sensors")
                
                with col2:
                    exclude_sensors_str = st.text_input("Exclude sensors (comma-separated numbers):", "")
                    exclude_sensors = []
                    if exclude_sensors_str:
                        try:
                            exclude_sensors = [int(x.strip()) for x in exclude_sensors_str.split(",")]
                        except:
                            st.error("Invalid format for exclude sensors")
            
            # Google API key for AI analysis
            with st.expander("AI Analysis Settings"):
                api_key = st.text_input("Google Generative AI API Key (optional):", type="password")
            
            # Analysis button
            if st.button("Analyze Data"):
                with st.spinner("Analyzing data... This may take a few minutes."):
                    # 1. Filter data
                    selected_data, sensor_columns_temp, sensor_columns_humidity = filter_data_by_time_and_sensors(
                        st.session_state.all_data, 
                        start_time, 
                        end_time, 
                        start_sensor, 
                        end_sensor,
                        additional_sensors,
                        exclude_sensors
                    )
                    
                    if len(selected_data) == 0:
                        st.error("❌ No data found for the selected time period.")
                    else:
                        # Display data preview
                        st.success(f"✅ Found {len(selected_data)} data points for analysis")
                        with st.expander("Preview Raw Data"):
                            st.dataframe(selected_data.head(10))
                        
                        # 2. Check for data loss
                        st.subheader("Data Loss Check")
                        data_loss_results, data_loss_warnings = check_data_loss(selected_data, start_sensor)
                        
                        if data_loss_warnings:
                            st.warning("\n".join(data_loss_warnings))
                        else:
                            st.success("✅ No significant data loss detected")
                        
                        with st.expander("View Detailed Data Loss Report"):
                            st.text("\n".join(data_loss_results))
                        
                        # 3. Fill missing data
                        filled_data = vtn_imputation(selected_data, sensor_columns_temp, sensor_columns_humidity)
                        
                        # 4. Store processed data for tab 3
                        st.session_state.filled_data = filled_data
                        st.session_state.sensor_columns_temp = sensor_columns_temp
                        st.session_state.sensor_columns_humidity = sensor_columns_humidity
                        st.session_state.room_number = room_number
                        st.session_state.room_name = room_name
                        st.session_state.start_sensor = start_sensor
                        st.session_state.end_sensor = end_sensor
                        
                        # 5. Calculate statistics
                        temp_stats, humidity_stats = calculate_statistics(
                            filled_data, sensor_columns_temp, sensor_columns_humidity
                        )
                        st.session_state.temp_stats = temp_stats
                        st.session_state.humidity_stats = humidity_stats
                        
                        # 6. Get AI analysis
                        ai_analysis = get_ai_analysis(temp_stats, humidity_stats, room_number, room_name, api_key)
                        st.session_state.ai_analysis = ai_analysis
                        
                        # 7. Export results
                        export_path = export_statistics_to_excel(
                            temp_stats, humidity_stats, room_number, room_name, "data/reports"
                        )
                        st.session_state.export_path = export_path
                        
                        # 8. Save processed data to CSV
                        csv_export_path = os.path.join("data/reports", f"{room_number}_{room_name}_processed_data.csv")
                        filled_data.to_csv(csv_export_path, index=False)
                        st.session_state.csv_export_path = csv_export_path
                        
                        st.session_state.analysis_done = True
                        st.success("✅ Analysis completed successfully! Go to Results tab to view.")

# Tab 3: Results
with tab3:
    st.header("Analysis Results")
    
    if not st.session_state.analysis_done:
        st.warning("⚠️ Please complete data analysis in the Analysis tab first.")
    else:
        # Display charts
        st.subheader("Temperature Chart")
        temp_chart = create_temperature_chart(
            st.session_state.filled_data, 
            st.session_state.sensor_columns_temp, 
            st.session_state.room_number, 
            st.session_state.room_name,
            st.session_state.start_sensor,
            st.session_state.end_sensor
        )
        st.plotly_chart(temp_chart, use_container_width=True)
        
        st.subheader("Humidity Chart")
        humidity_chart = create_humidity_chart(
            st.session_state.filled_data, 
            st.session_state.sensor_columns_humidity, 
            st.session_state.room_number, 
            st.session_state.room_name,
            st.session_state.start_sensor,
            st.session_state.end_sensor
        )
        st.plotly_chart(humidity_chart, use_container_width=True)
        
        # Display statistics
        st.subheader("Statistical Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Temperature Statistics**")
            st.dataframe(st.session_state.temp_stats, use_container_width=True)
        
        with col2:
            st.markdown("**Humidity Statistics**")
            st.dataframe(st.session_state.humidity_stats, use_container_width=True)
        
        # Display AI analysis
        st.subheader("AI Analysis Report")
        st.markdown(st.session_state.ai_analysis)
        
        # Download options
        st.subheader("Download Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(get_excel_download_link(
                st.session_state.export_path, 
                "📊 Download Statistics Excel Report"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(get_csv_download_link(
                st.session_state.filled_data,
                f"{st.session_state.room_number}_{st.session_state.room_name}_processed_data.csv",
                "📈 Download Processed CSV Data"
            ), unsafe_allow_html=True)

# Add footer
st.markdown("---")
st.markdown("**Temperature & Humidity Mapping Analysis Tool** | Built with Streamlit")
