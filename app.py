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
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    try:
        # 1. 登入
        res_l = session.get(LOGIN_URL)
        soup_l = BeautifulSoup(res_l.text, 'html.parser')
        payload_l = {tag.get('name'): tag.get('value', '') for tag in soup_l.find_all('input') if tag.get('name')}
        # 對接正確的欄位名稱
        payload_l.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u, 
            "ctl00$ContentPlaceHolder1$txtPass": p, 
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })
        login_res = session.post(LOGIN_URL, data=payload_l)
        
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "登入失敗：請檢查帳號密碼是否正確。"

        # 2. 打卡
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
        
        # 3. 解析 3591 字元封包
        if "簽到完成" in response.text:
            time_m = re.search(r'lb_time".*?>(.*?)</span>', response.text)
            punch_time = time_m.group(1) if time_m else "伺服器已記錄"
            return True, f"簽到成功！\n\n系統紀錄時間：{punch_time}"
        else:
            clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"簽到未完成：{clean_msg if clean_msg else '座標或權限異常'}"

    except Exception as e:
        return False, f"連線錯誤: {str(e)}"

# --- 點擊執行 ---
if punch_btn:
    if not u_id or not u_pw:
        st.warning("👈 請先在左側輸入帳號密碼並點擊確認。")
    else:
        with st.spinner("傳送座標中..."):
            success, msg = run_punch(u_id, u_pw, selected_lat, selected_lon)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)