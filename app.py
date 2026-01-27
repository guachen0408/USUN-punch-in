import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# 陽程科技精確座標
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

# 初始化座標狀態
if 'lat' not in st.session_state:
    st.session_state.lat = SUNNY_TEC_COORDS[0]
if 'lon' not in st.session_state:
    st.session_state.lon = SUNNY_TEC_COORDS[1]

# --- 側邊欄：登入資訊 ---
with st.sidebar:
    st.header("🔐 員工登入")
    with st.form("login_info"):
        u_id = st.text_input("工號", placeholder="請輸入工號")
        u_pw = st.text_input("密碼", type="password")
        submit_form = st.form_submit_button("確認登入資訊", use_container_width=True)

# --- 主畫面佈局 ---
st.title("📍 陽程科技定向簽到")

# 資訊列與按鈕
inf1, inf2, btn_col = st.columns([2, 2, 2])
# 使用 placeholder 確保數據更新時更流暢
lat_display = inf1.empty()
lon_display = inf2.empty()

with btn_col:
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 地圖處理 ---
def create_map(lat, lon):
    m = folium.Map(location=[lat, lon], zoom_start=18)
    LocateControl(auto_start=False, flyTo=True).add_to(m)
    
    # 動態標記：這會跟著 lat, lon 移動
    folium.Marker(
        [lat, lon], 
        popup="打卡位置", 
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)
    
    # 點擊顯示座標提示 (非同步更新主要靠 st_folium 回傳)
    m.add_child(folium.LatLngPopup())
    return m

# 顯示地圖，透過 fixed key 避免全頁刷新
map_data = st_folium(
    create_map(st.session_state.lat, st.session_state.lon),
    height=500,
    use_container_width=True,
    key="punch_map" # 關鍵：固定 key 值
)

# 當點擊發生時，僅更新內部數據
if map_data and map_data.get("last_clicked"):
    new_lat = map_data["last_clicked"]["lat"]
    new_lon = map_data["last_clicked"]["lng"]
    
    # 如果座標改變，才更新 session_state
    if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
        st.session_state.lat = new_lat
        st.session_state.lon = new_lon
        st.rerun() # 為了同步 Marker 位置，這一步目前在 Streamlit 仍需 rerun 但會比沒 key 快很多

# 更新上方數據顯示
lat_display.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
lon_display.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

# --- 簽到邏輯與執行 (run_punch) ---
# ... (保持之前提供的邏輯) ...