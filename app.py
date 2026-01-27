import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# 設定網頁外觀
st.set_page_config(page_title="USUN 自動打卡系統", page_icon="📍")
st.title("📍 USUN 線上打卡工具")
st.markdown("請輸入員工資訊執行遠端打卡。密碼僅供本次連線使用，不進行儲存。")

# --- 側邊欄：使用者設定 ---
st.sidebar.header("🔐 員工登入資訊")
user_id = st.sidebar.text_input("員工帳號 (User ID)")
user_pw = st.sidebar.text_input("登入密碼 (Password)", type="password")

st.sidebar.header("🌐 地理位置設定")
st.sidebar.info("預設為公司附近座標，可手動修改。")
lat = st.sidebar.text_input("緯度 (Latitude)", value="25.0544957")
lon = st.sidebar.text_input("經度 (Longitude)", value="121.1971982")

# --- 核心邏輯函數 ---
def run_punch_flow(u, p, la, lo):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    def get_asp_fields(soup):
        return {f: soup.find('input', {'id': f})['value'] for f in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"] if soup.find('input', {'id': f})}

    try:
        # 1. 登入階段
        login_page = session.get(LOGIN_URL)
        login_soup = BeautifulSoup(login_page.text, 'html.parser')
        login_payload = get_asp_fields(login_soup)
        
        login_payload.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u,
            "ctl00$ContentPlaceHolder1$txtPass": p,
            "ctl00$ContentPlaceHolder1$btn_login": "登入",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": ""
        })
        
        login_res = session.post(LOGIN_URL, data=login_payload, allow_redirects=True)
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：請確認帳號密碼是否正確。"

        # 2. 準備打卡階段
        punch_page = session.get(PUNCH_URL)
        punch_soup = BeautifulSoup(punch_page.text, 'html.parser')
        punch_payload = get_asp_fields(punch_soup)
        
        if not punch_payload.get("__VIEWSTATE"):
            return False, "❌ 權限錯誤：無法獲取打卡驗證碼 (ViewState)，請重新嘗試。"

        # 3. 發送 Ajax 打卡請求
        punch_payload.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$longitude": lo,
            "ctl00$ContentPlaceHolder1$latitude": la,
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })

        ajax_headers = {
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": PUNCH_URL,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

        response = session.post(PUNCH_URL, data=punch_payload, headers=ajax_headers)
        
        # 4. 解析結果
        if "成功" in response.text:
            return True, "🎉 打卡成功！已完成系統紀錄。"
        
        # 處理 Ajax 回傳的複雜內容，提取中文字幕
        raw_text = response.text
        # 過濾掉 HTML 標籤與特殊字元，只保留中文提示
        clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', raw_text))
        
        # 針對常見錯誤進行轉換
        if "跳轉" in clean_msg or "login" in raw_text.lower():
            return False, "⚠️ 登入逾時：請重新執行。"
        elif clean_msg:
            return False, f"⚠️ 系統提示：{clean_msg}"
        else:
            return False, f"❓ 未知狀態 (Code: {response.status_code})，建議至官網檢查。"

    except Exception as e:
        return False, f"💥 系統崩潰: {str(e)}"

# --- 主畫面按鈕 ---
if st.button("🚀 執行打卡", use_container_width=True):
    if not user_id or not user_pw:
        st.warning("請先填寫帳號與密碼。")
    else:
        with st.status("正在連線至公司系統...", expanded=True) as status:
            st.write("正在驗證帳號密碼...")
            success, message = run_punch_flow(user_id, user_pw, lat, lon)
            
            if success:
                status.update(label="打卡執行完畢", state="complete", expanded=False)
                st.success(message)
                st.balloons()
            else:
                status.update(label="執行終止", state="error", expanded=True)
                st.error(message)
                st.info("💡 提示：若出現『不在範圍內』，可能因伺服器位於海外被阻擋，建議改用家中小電腦部署。")

st.divider()
st.caption("本工具僅供技術研究使用。請遵守公司打卡規範。")