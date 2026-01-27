import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import extra_streamlit_components as stx
from datetime import datetime, timedelta

st.set_page_config(page_title="USUN 記憶簽到", page_icon="📝", layout="centered")

# --- 1. 初始化 Cookie 管理器 ---
cookie_manager = stx.CookieManager(key="punch_cookie_manager")

# --- 2. 讀取 Cookie (確保讀取穩定) ---
# 獲取所有 Cookie，如果尚未讀取到則給予空字典
all_cookies = cookie_manager.get_all()
saved_id = all_cookies.get("u_id", "")
saved_pw = all_cookies.get("u_pw", "")

st.title("📝 USUN 個人簽到系統")
st.markdown("---")

st.subheader("🔐 員工登入")

# 使用 key 確保欄位狀態被 Streamlit 正確追蹤
u_id = st.text_input("工號", value=saved_id, placeholder="請輸入工號", key="id_input")
u_pw = st.text_input("密碼", type="password", value=saved_pw, placeholder="請輸入密碼", key="pw_input")

submit_btn = st.button("🚀 執行簽到並記住在此裝置", use_container_width=True, type="primary")

# --- 3. 核心簽到邏輯 (強化 Ajax 版本) ---
def run_punch(u, p):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    # 模擬完整瀏覽器標頭
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    })

    try:
        # 1. 登入階段
        res_l = session.get(LOGIN_URL)
        soup_l = BeautifulSoup(res_l.text, 'html.parser')
        payload_l = {tag.get('name'): tag.get('value', '') for tag in soup_l.find_all('input') if tag.get('name')}
        payload_l.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u, 
            "ctl00$ContentPlaceHolder1$txtPass": p, 
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })
        login_res = session.post(LOGIN_URL, data=payload_l)
        
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：帳號或密碼錯誤。"

        # 2. 準備簽到頁面資料 (獲取 ViewState)
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        
        # 3. 發送 Ajax 簽到指令 (完全模擬 3591 字元結構)
        payload_p.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__EVENTARGUMENT": "",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })

        ajax_headers = {
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": PUNCH_URL,
            "Origin": BASE_URL,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        
        # 檢查回傳內容
        if "簽到完成" in response.text:
            return True, "🎉 簽到完成！伺服器已成功記錄。"
        else:
            # 嘗試抓取系統回傳的中文錯誤訊息
            error_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"⚠️ 失敗：{error_msg if error_msg else '封包被拒絕，請檢查是否已簽到過'}"

    except Exception as e:
        return False, f"💥 通訊異常: {str(e)}"

# --- 4. 點擊動作 ---
if submit_btn:
    if u_id and u_pw:
        # 更新 Cookie (保持 30 天)
        expiry = datetime.now() + timedelta(days=30)
        cookie_manager.set("u_id", u_id, expires_at=expiry)
        cookie_manager.set("u_pw", u_pw, expires_at=expiry)
        
        with st.spinner("同步簽到資訊中..."):
            success, msg = run_punch(u_id, u_pw)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)
    else:
        st.warning("請完整輸入資訊。")