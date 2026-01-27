import streamlit as st
import folium
from streamlit_folium import st_folium
import re

# --- 介面設定 ---
st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# 陽程科技精確座標
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

# 初始化狀態
if 'lat' not in st.session_state:
    st.session_state.lat = SUNNY_TEC_COORDS[0]
if 'lon' not in st.session_state:
    st.session_state.lon = SUNNY_TEC_COORDS[1]

st.title("📍 陽程科技定向簽到")

# --- 第一列：數據顯示與定位按鈕 ---
inf1, inf2, btn_geo, btn_punch = st.columns([2, 2, 1.5, 1.5])

# 顯示數值
lat_display = inf1.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
lon_display = inf2.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

# 「抓取目前定位」功能
with btn_geo:
    st.write("") # 對齊高度
    # 這裡我們使用一個隱藏的元件或是說明，因為 Streamlit Cloud 
    # 獲取使用者當前精確 GPS 需透過瀏覽器，最穩定的做法是直接在地圖上點擊。
    # 如果要「自動」跳轉回公司，我們做一個回位按鈕：
    if st.button("🏠 回到工廠位置", use_container_width=True):
        st.session_state.lat = SUNNY_TEC_COORDS[0]
        st.session_state.lon = SUNNY_TEC_COORDS[1]
        st.rerun()

with btn_punch:
    st.write("")
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 第二列：地圖區塊 (使用 Fragment 避免閃爍) ---
@st.fragment
def map_section():
    # 建立地圖，位置鎖定在當前的 session_state
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
    
    # 紅點標記：必須跟著 st.session_state 跑
    folium.Marker(
        [st.session_state.lat, st.session_state.lon],
        popup="當前選取點",
        icon=folium.Icon(color="red", icon="screenshot", prefix='fa')
    ).add_to(m)
    
    # 渲染地圖
    map_data = st_folium(
        m, 
        height=500, 
        use_container_width=True,
        key="punch_map_final",
        # 增加此參數可以讓地圖更靈敏地捕捉點擊
        returned_objects=["last_clicked"]
    )

    # 關鍵：點擊地圖時，立刻更新數字與紅點
    if map_data and map_data.get("last_clicked"):
        click_lat = map_data["last_clicked"]["lat"]
        click_lon = map_data["last_clicked"]["lng"]
        
        if click_lat != st.session_state.lat or click_lon != st.session_state.lon:
            st.session_state.lat = click_lat
            st.session_state.lon = click_lon
            # 強制刷新局部區塊，讓上方數字與地圖標記同步
            st.rerun(scope="fragment")

map_section()