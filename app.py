import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍", layout="wide")

# --- 側邊欄：登入表單 ---
with st.sidebar:
    st.header("🔐 員工登入")
    with st.form("login_info"):
        u_id = st.text_input("工號", placeholder="請輸入工號")
        u_pw = st.text_input("密碼", type="password", placeholder="請輸入密碼")
        submit_form = st.form_submit_button("確認登入資訊", use_container_width=True)

# --- 主畫面 ---
st.title("📍 陽程科技定向簽到")

# 陽程科技精確座標
SUNNY_TEC_COORDS = [25.0478546, 121.1903687]

# 1. 地圖上方顯示目前的精確座標 (讓它看起來像地圖的一部分)
# 預設值設定
if 'lat' not in st.session_state:
    st.session_state.lat = SUNNY_TEC_COORDS[0]
if 'lon' not in st.session_state:
    st.session_state.lon = SUNNY_TEC_COORDS[1]

# 建立橫向資訊列
inf1, inf2, btn_col = st.columns([2, 2, 2])
inf1.metric("緯度 Latitude", f"{st.session_state.lat:.7f}")
inf2.metric("經度 Longitude", f"{st.session_state.lon:.7f}")

# 2. 核心操作按鈕 (放置在最顯眼的地方)
with btn_col:
    st.write("") # 對齊 metric 的高度
    punch_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")

# 3. 地圖區域
m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
LocateControl(auto_start=False, flyTo=True).add_to(m)
folium.Marker(SUNNY_TEC_COORDS, popup="陽程科技總部", icon=folium.Icon(color="red")).add_to(m)
m.add_child(folium.LatLngPopup())

# 顯示地圖並獲取點擊
map_data = st_folium(m, height=500, use_container_width=True)

# 當地圖被點擊時，更新 session_state 並觸發重新渲染
if map_data and map_data.get("last_clicked"):
    st.session_state.lat = map_data["last_clicked"]["lat"]
    st.session_state.lon = map_data["last_clicked"]["lng"]
    st.rerun() # 立即更新上方 metric 顯示

# --- 簽到邏輯函數 (run_punch) 保持不變 ---
def run_punch(u, p, la, lo):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        res_l = session.get(LOGIN_URL)
        soup_l = BeautifulSoup(res_l.text, 'html.parser')
        payload_l = {tag.get('name'): tag.get('value', '') for tag in soup_l.find_all('input') if tag.get('name')}
        payload_l.update({"ctl00$ContentPlaceHolder1$txtLogin": u, "ctl00$ContentPlaceHolder1$txtPass": p, "ctl00$ContentPlaceHolder1$btn_login": "登入"})
        login_res = session.post(LOGIN_URL, data=payload_l)
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "登入失敗：請檢查帳密。"
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        payload_p.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$longitude": lo,
            "ctl00$ContentPlaceHolder1$latitude": la,
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })
        ajax_headers = {"X-MicrosoftAjax": "Delta=true", "X-Requested-With": "XMLHttpRequest", "Referer": PUNCH_URL}
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        if "簽到完成" in response.text:
            time_m = re.search(r'lb_time".*?>(.*?)</span>', response.text)
            return True, f"簽到成功！\n\n系統時間：{time_m.group(1) if time_m else '已記錄'}"
        return False, "簽到未完成，請檢查座標範圍。"
    except Exception as e:
        return False, f"連線錯誤: {str(e)}"

# --- 點擊按鈕執行 ---
if punch_btn:
    if not u_id or not u_pw:
        st.error("👈 請先完成左側登入表單")
    else:
        with st.spinner("🚀 座標傳送中..."):
            success, msg = run_punch(u_id, u_pw, st.session_state.lat, st.session_state.lon)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)