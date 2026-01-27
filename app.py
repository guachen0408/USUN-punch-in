import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import re

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# 陽程科技精確座標
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

# 初始化狀態，避免刷新時遺失數據
if 'lat' not in st.session_state:
    st.session_state.lat = SUNNY_TEC_COORDS[0]
if 'lon' not in st.session_state:
    st.session_state.lon = SUNNY_TEC_COORDS[1]

# --- 側邊欄：登入資訊 (這部分不會受地圖點擊影響) ---
with st.sidebar:
    st.header("🔐 員工登入")
    with st.form("login_info"):
        u_id = st.text_input("工號")
        u_pw = st.text_input("密碼", type="password")
        st.form_submit_button("確認登入資訊")

st.title("📍 陽程科技定向簽到")

# 建立上方資訊列
inf1, inf2, btn_col = st.columns([2, 2, 2])
lat_display = inf1.empty()
lon_display = inf2.empty()

# --- 定義局部刷新區塊 ---
@st.fragment
def map_section():
    # 建立地圖物件
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
    LocateControl(auto_start=False, flyTo=True).add_to(m)
    
    # 紅點標記：固定綁定 session_state
    folium.Marker(
        [st.session_state.lat, st.session_state.lon],
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    
    # 渲染地圖
    map_data = st_folium(
        m, 
        height=500, 
        use_container_width=True,
        key="punch_map_fragment" # 關鍵：固定 Key
    )

    # 處理點擊事件：僅更新 state，不觸發整頁 rerun
    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]
        if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            # 這裡不使用 st.rerun()，而是讓 fragment 自行處理
            st.rerun(scope="fragment")

# 執行局部地圖區塊
map_section()

# 更新上方顯示數值 (這部分會隨 state 改變)
lat_display.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
lon_display.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

with btn_col:
    st.write("")
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 簽到執行邏輯 ---
if punch_btn:
    # (執行之前的 run_punch 函數內容...)
    st.success(f"已嘗試以座標 {st.session_state.lat}, {st.session_state.lon} 簽到")