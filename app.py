import streamlit as st
import folium
from streamlit_folium import st_folium
import re

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# 陽程科技精確座標
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

# --- 1. 初始化所有狀態 (保險機制) ---
if 'lat' not in st.session_state:
    st.session_state.lat = SUNNY_TEC_COORDS[0]
if 'lon' not in st.session_state:
    st.session_state.lon = SUNNY_TEC_COORDS[1]
# 確保帳密欄位存在 state 中
if 'u_id_val' not in st.session_state:
    st.session_state.u_id_val = ""
if 'u_pw_val' not in st.session_state:
    st.session_state.u_pw_val = ""

# --- 2. 側邊欄：登入資訊 (加入固定 Key) ---
with st.sidebar:
    st.header("🔐 員工登入")
    # 使用 key 讓 Streamlit 強制記住這兩個欄位的值
    u_id = st.text_input("工號", key="u_id_val")
    u_pw = st.text_input("密碼", type="password", key="u_pw_val")
    st.info("💡 座標變動時，此處資料會被妥善保存。")

st.title("📍 陽程科技定向簽到")

# --- 3. 上方數據顯示列 ---
inf1, inf2, btn_punch = st.columns([3, 3, 2])

# 即時更新顯示 (與地圖同步)
inf1.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
inf2.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

with btn_punch:
    st.write("")
    # 這裡直接從 session_state 抓帳密
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# --- 4. 地圖區塊 (局部刷新，不影響側邊欄) ---
@st.fragment
def map_section():
    # 建立地圖
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
    
    # 增加定位控制 (JS 前端行為)
    from folium.plugins import LocateControl
    LocateControl(auto_start=False, flyTo=True, keepCurrentZoomLevel=True).add_to(m)
    
    # 紅點標記：這就是核心，我們監聽它的位置
    folium.Marker(
        [st.session_state.lat, st.session_state.lon],
        icon=folium.Icon(color="red", icon="crosshairs", prefix='fa')
    ).add_to(m)
    
    # 渲染地圖，監聽「最後點擊位置」
    map_data = st_folium(
        m, 
        height=500, 
        use_container_width=True,
        key="punch_map_final_safe", # 固定 Key 避免地圖重置
        returned_objects=["last_clicked"]
    )

    # 點擊地圖時同步更新座標
    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]
        
        if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            # 只重刷地圖區塊，不影響側邊欄 input
            st.rerun(scope="fragment")

map_section()

# --- 5. 執行打卡動作 ---
if punch_btn:
    # 從 session_state 讀取最新輸入的值
    user = st.session_state.u_id_val
    pw = st.session_state.u_pw_val
    
    if not user or not pw:
        st.error("❌ 請先輸入工號與密碼！")
    else:
        # 執行原本的 run_punch 函數
        st.toast(f"正在為 {user} 發送座標...")
        # (這裡接上你之前的 run_punch 邏輯)