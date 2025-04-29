import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def create_temperature_chart(filled_data, sensor_columns_temp, room_number, room_name, start_sensor, end_sensor):
    """สร้างกราฟอุณหภูมิ"""
    # สร้างชุดสี
    color_scale = px.colors.qualitative.Plotly
    num_sensors = len(sensor_columns_temp)
    colors = color_scale * (num_sensors // len(color_scale) + 1)
    colors = colors[:num_sensors]
    
    # สร้างกราฟ
    fig = go.Figure()
    
    for i, sensor in enumerate(sensor_columns_temp):
        sensor_number = sensor.replace("TempSensor", "")
        color = colors[i]
        fig.add_trace(
            go.Scatter(
                x=filled_data['timestamp'],
                y=filled_data[sensor],
                mode='lines',
                name=f"Temp{sensor_number}",
                line=dict(color=color)
            )
        )
    
    # ปรับแต่ง layout
    fig.update_layout(
        title=dict(
            text=f"<b>Temperature Trends for {room_number}: {room_name} from Sensor {start_sensor} to {end_sensor}</b>",
            font=dict(size=15, family="Arial", color="black")
        ),
        legend_title="Sensors",
        template="plotly",
        height=500,
        width=900,
        showlegend=True,
        xaxis=dict(title="Time"),
        yaxis=dict(title="Temperature Value (C)")
    )
    
    return fig

def create_humidity_chart(filled_data, sensor_columns_humidity, room_number, room_name, start_sensor, end_sensor):
    """สร้างกราฟความชื้น"""
    # สร้างชุดสี
    color_scale = px.colors.qualitative.Plotly
    num_sensors = len(sensor_columns_humidity)
    colors = color_scale * (num_sensors // len(color_scale) + 1)
    colors = colors[:num_sensors]
    
    # สร้างกราฟ
    fig = go.Figure()
    
    for i, sensor in enumerate(sensor_columns_humidity):
        sensor_number = sensor.replace("RHSensor", "")
        color = colors[i]
        fig.add_trace(
            go.Scatter(
                x=filled_data['timestamp'],
                y=filled_data[sensor],
                mode='lines',
                name=f"Hum{sensor_number}",
                line=dict(color=color)
            )
        )
    
    # ปรับแต่ง layout
    fig.update_layout(
        title=dict(
            text=f"<b>Humidity Trends for {room_number}: {room_name} from Sensor {start_sensor} to {end_sensor}</b>",
            font=dict(size=15, family="Arial", color="black")
        ),
        legend_title="Sensors",
        template="plotly",
        height=500,
        width=900,
        showlegend=True,
        xaxis=dict(title="Time"),
        yaxis=dict(title="Humidity Value (%RH)")
    )
    
    return fig
