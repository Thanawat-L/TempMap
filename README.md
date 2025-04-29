# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

temperature-mapping-app/
├── app.py                  # ไฟล์หลักของ Streamlit app
├── utils/
│   ├── __init__.py
│   ├── data_processor.py   # ฟังก์ชันสำหรับประมวลผลข้อมูล
│   ├── visualization.py    # ฟังก์ชันสำหรับสร้างกราฟ
│   └── analysis.py         # ฟังก์ชันสำหรับวิเคราะห์ข้อมูลสถิติ
├── requirements.txt        # แพ็คเกจที่จำเป็น
└── data/                   # โฟลเดอร์สำหรับเก็บข้อมูลชั่วคราว
    ├── csv/                # โฟลเดอร์สำหรับไฟล์ CSV
    ├── excel/              # โฟลเดอร์สำหรับไฟล์ Excel
    ├── reports/            # โฟลเดอร์สำหรับรายงานผลลัพธ์
    └── temp/               # โฟลเดอร์สำหรับไฟล์ชั่วคราว
