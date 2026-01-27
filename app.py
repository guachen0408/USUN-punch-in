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

# --- 第一列：數據顯示與執行按鈕 ---
inf1, inf2, btn_punch = st.columns([3, 3, 2])

# 使用 empty 容器確保數字更新時不會閃爍
lat_container = inf1.empty()
lon_container = inf2.empty()

# 更新上方顯示數值
lat_container.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
lon_container.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

with btn_punch:
    st.write("")
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 第二列：地圖區塊 ---
@st.fragment
def map_section():
    # 建立地圖
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
    
    from folium.plugins import LocateControl
    # 增加定位控制，並讓它點擊後自動追蹤
    LocateControl(auto_start=False, flyTo=True, keepCurrentZoomLevel=True).add_to(m)
    
    # 紅點標記：這就是核心，我們監聽它的位置
    folium.Marker(
        [st.session_state.lat, st.session_state.lon],
        icon=folium.Icon(color="red", icon="crosshairs", prefix='fa'),
        draggable=True # 讓紅點可以拖動
    ).add_to(m)
    
    # 渲染地圖，監聽「最後點擊位置」
    map_data = st_folium(
        m, 
        height=500, 
        use_container_width=True,
        key="punch_map_auto_update",
        returned_objects=["last_clicked", "zoom"] # 監聽數據回傳
    )

    # 核心連動邏輯：只要地圖回傳了新位置，立刻更新數字
    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]
        
        if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
            # 更新 Session State
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            # 觸發局部更新，這會讓上方的 metric 自動同步變換
            st.rerun(scope="fragment")

map_section()