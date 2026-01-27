import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl

st.set_page_config(page_title="陽程科技簽到系統", page_icon="📍")
st.title("📍 陽程科技 - 地圖定位簽到")

# --- 側邊欄：登入資訊 ---
st.sidebar.header("🔐 員工登入")
u_id = st.sidebar.text_input("工號")
u_pw = st.sidebar.text_input("密碼", type="password")

# --- 主畫面：地圖選擇區 ---
st.subheader("第一步：選取簽到位置")

# 陽程科技 (大園總部) 的精確座標
SUNNY_TEC_COORDS = [25.054495, 121.197198]

# 建立地圖：預設位置在陽程科技
m = folium.Map(location=SUNNY_TEC_COORDS, zoom_start=17)

# 添加「目前定位」按鈕 (需要瀏覽器權限)
LocateControl(auto_start=False, flyTo=True, keepCurrentZoomLevel=True).add_to(m)

# 添加一個紅點標記在陽程科技，方便辨識
folium.Marker(
    SUNNY_TEC_COORDS, 
    popup="陽程科技總部", 
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)

# 點擊地圖顯示座標的小視窗
m.add_child(folium.LatLngPopup())

# 顯示地圖並抓取數據
map_data = st_folium(m, height=450, width=700)

# 邏輯：獲取點擊後的座標，若沒點擊則預設為陽程科技
selected_lat = SUNNY_TEC_COORDS[0]
selected_lon = SUNNY_TEC_COORDS[1]

if map_data and map_data.get("last_clicked"):
    selected_lat = map_data["last_clicked"]["lat"]
    selected_lon = map_data["last_clicked"]["lng"]

# 座標預覽區
st.info(f"📍 當前選取的簽到座標：{selected_lat} , {selected_lon}")

# --- 簽到核心邏輯 ---
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
        payload_l.update({"ctl00$ContentPlaceHolder1$txtLogin": u, "ctl00$ContentPlaceHolder1$txtPass": p, "ctl00$ContentPlaceHolder1$btn_login": "登入"})
        login_res = session.post(LOGIN_URL, data=payload_l)
        
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：請確認帳號密碼。"

        # 2. 獲取打卡頁 ViewState
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        
        # 3. 發送打卡 (Ajax 格式)
        payload_p.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$longitude": lo,
            "ctl00$ContentPlaceHolder1$latitude": la,
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })

        ajax_headers = {"X-MicrosoftAjax": "Delta=true", "X-Requested-With": "XMLHttpRequest", "Referer": PUNCH_URL}
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        raw_res = response.text

        # 4. 解析回傳內容 (使用我們之前解析成功的邏輯)
        if "簽到完成" in raw_res:
            time_m = re.search(r'lb_time".*?>(.*?)</span>', raw_res)
            punch_time = time_m.group(1) if time_m else "剛才"
            return True, f"🎉 簽到完成！\n\n系統紀錄時間：{punch_time}"
        else:
            # 提取錯誤訊息
            clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', raw_res))
            return False, f"⚠️ 簽到未成功。系統訊息：{clean_msg}"

    except Exception as e:
        return False, f"💥 錯誤: {str(e)}"

# --- 執行按鈕 ---
st.subheader("第二步：發送簽到")
if st.button("🚀 確認位置並送出簽到", use_container_width=True):
    if not u_id or not u_pw:
        st.error("請在左側選單輸入帳號密碼")
    else:
        with st.spinner("正在通訊中..."):
            success, msg = run_punch(u_id, u_pw, selected_lat, selected_lon)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)