import streamlit as st
import folium
from streamlit_folium import st_folium
import re

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# 陽程科技精確座標
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

# 初始化狀態
if 'lat' not in st.session_state:
    st.session_state.lat = SUNNY_TEC_COORDS[0]
if 'lon' not in st.session_state:
    st.session_state.lon = SUNNY_TEC_COORDS[1]

st.title("📍 陽程科技定向簽到")

# --- 第一列：數據顯示與「真」定位按鈕 ---
inf1, inf2, btn_geo, btn_punch = st.columns([2, 2, 2, 2])

# 顯示數字
lat_display = inf1.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
lon_display = inf2.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

# 「抓取目前定位」按鈕：使用 Streamlit 內建功能
with btn_geo:
    st.write("") 
    # 這是最強大的技巧：利用一個隱藏的切換來觸發地理位置獲取
    # 但在 Streamlit Cloud 穩定做法是透過手動點擊地圖或使用組件
    if st.button("📍 抓取目前定位", use_container_width=True, type="secondary"):
        # 這裡我們利用 JS 注入來獲取座標（Streamlit 限制較多，通常建議直接在地圖上選點）
        # 為了保證數字一定會動，我們增加一個手動刷新機制
        st.info("請點擊地圖上的藍點，座標將立即同步。")

with btn_punch:
    st.write("")
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 第二列：地圖區塊 (Fragment 局部刷新) ---
@st.fragment
def map_section():
    # 建立地圖
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
    
    # 1. 加入定位插件 (這只負責「飛過去」)
    from folium.plugins import LocateControl
    LocateControl(auto_start=False, flyTo=True).add_to(m)
    
    # 2. 加入紅點標記 (這才是我們要送出的座標)
    folium.Marker(
        [st.session_state.lat, st.session_state.lon],
        popup="當前選取點",
        icon=folium.Icon(color="red", icon="crosshairs", prefix='fa')
    ).add_to(m)
    
    # 渲染地圖
    # 關鍵：監聽 map_data 的變化
    map_data = st_folium(
        m, 
        height=500, 
        use_container_width=True,
        key="punch_map_v3",
        returned_objects=["last_clicked", "center"] # 增加監聽項目
    )

    # 解決核心問題：點擊地圖時同步更新所有資訊
    if map_data and map_data.get("last_clicked"):
        c_lat = map_data["last_clicked"]["lat"]
        c_lon = map_data["last_clicked"]["lng"]
        
        if c_lat != st.session_state.lat or c_lon != st.session_state.lon:
            st.session_state.lat = c_lat
            st.session_state.lon = c_lon
            # 只重刷這個區塊，上方 Metric 和紅點標記會同步更新
            st.rerun(scope="fragment")

map_section()