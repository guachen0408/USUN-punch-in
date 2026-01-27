import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# --- 側邊欄：登入表單 (觸發瀏覽器自動填入) ---
with st.sidebar:
    st.header("🔐 員工登入")
    with st.form("login_info"):
        u_id = st.text_input("工號", placeholder="請輸入工號")
        u_pw = st.text_input("密碼", type="password", placeholder="請輸入密碼")
        st.caption("💡 點擊下方按鈕後，瀏覽器將詢問是否記憶帳密。")
        submit_form = st.form_submit_button("確認登入資訊", use_container_width=True)

# --- 主畫面：地圖定位區 ---
st.title("📍 陽程科技 - 定位簽到系統")

# 陽程科技精確座標 (聖德北路 68 號)
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("1. 選取位置")
    # 建立地圖
    m = folium.Map(location=SUNNY_TEC_COORDS, zoom_start=18)
    LocateControl(auto_start=False, flyTo=True).add_to(m) # 目前定位按鈕
    folium.Marker(SUNNY_TEC_COORDS, popup="陽程科技", icon=folium.Icon(color="red")).add_to(m)
    m.add_child(folium.LatLngPopup()) # 點擊顯示座標
    
    map_data = st_folium(m, height=450, use_container_width=True)

# 獲取座標邏輯
selected_lat, selected_lon = SUNNY_TEC_COORDS
if map_data and map_data.get("last_clicked"):
    selected_lat = map_data["last_clicked"]["lat"]
    selected_lon = map_data["last_clicked"]["lng"]

with col2:
    st.subheader("2. 簽到狀態")
    st.write(f"📌 **當前座標**")
    st.code(f"{selected_lat}\n{selected_lon}")
    
    # 執行按鈕
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 核心簽到邏輯 ---
def run_punch(u, p, la, lo):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal