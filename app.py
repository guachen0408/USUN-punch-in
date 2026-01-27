import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="USUN 地圖簽到系統", page_icon="🗺️")
st.title("🗺️ USUN 地圖選點簽到")

# --- 側邊欄：登入資訊 ---
st.sidebar.header("🔐 員工資訊")
u_id = st.sidebar.text_input("帳號")
u_pw = st.sidebar.text_input("密碼", type="password")

# --- 主畫面：地圖選擇區 ---
st.subheader("📍 第一步：在地圖上選擇打卡位置")
st.info("請點擊地圖上的位置，下方會自動更新座標。")

# 設定預設座標 (公司位置)
default_lat, default_lon = 25.0544957, 121.1971982

# 建立地圖物件
m = folium.Map(location=[default_lat, default_lon], zoom_start=16)
# 加入點擊監聽
m.add_child(folium.LatLngPopup())

# 顯示地圖並獲取點擊數據
map_data = st_folium(m, height=400, width=700)

# 獲取點擊後的座標，若沒點擊則用預設值
selected_lat = default_lat
selected_lon = default_lon

if map_data and map_data.get("last_clicked"):
    selected_lat = map_data["last_clicked"]["lat"]
    selected_lon = map_data["last_clicked"]["lng"]

# 顯示當前選取的座標 (唯讀，方便確認)
col1, col2 = st.columns(2)
with col1:
    st.success(f"當前緯度: {selected_lat}")
with col2:
    st.success(f"當前經度: {selected_lon}")

# --- 核心打卡函數 (與之前邏輯相同) ---
def run_punch(u, p, la, lo):
    # ... (此處保留之前的 run_punch 邏輯內容) ...
    # 確保參數帶入 la 和 lo
    pass

# --- 執行按鈕 ---
st.subheader("🚀 第二步：執行簽到")
if st.button("確認位置並執行簽到", use_container_width=True):
    if not u_id or not u_pw:
        st.error("請先填寫左側帳號密碼！")
    else:
        # 呼叫打卡邏輯 (這部分沿用之前的函數)
        # 這裡簡化顯示，實際請放入之前的 run_punch 函數
        with st.spinner("通訊中..."):
            # 這裡帶入 selected_lat, selected_lon
            st.write(f"正在以座標 ({selected_lat}, {selected_lon}) 簽到...")
            # 成功/失敗判斷邏輯...