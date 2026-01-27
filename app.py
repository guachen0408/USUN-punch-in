import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import extra_streamlit_components as stx
from datetime import datetime, timedelta

st.set_page_config(page_title="USUN Cookie 簽到", page_icon="📝", layout="centered")

# --- 1. 初始化 Cookie 管理器 ---
cookie_manager = stx.CookieManager()

# --- 2. 讀取 Cookie (一開網頁就抓取) ---
# 這裡嘗試從瀏覽器抓取之前的紀錄
saved_id = cookie_manager.get(cookie="u_id")
saved_pw = cookie_manager.get(cookie="u_pw")

st.title("📝 USUN 個人簽到系統")
st.markdown("---")

st.subheader("🔐 員工登入")

# 將抓到的 Cookie 填入 value，達成「一開頁面就顯示」
u_id = st.text_input("工號", value=saved_id if saved_id else "", placeholder="請輸入工號")
u_pw = st.text_input("密碼", type="password", value=saved_pw if saved_pw else "", placeholder="請輸入密碼")

submit_btn = st.button("🚀 執行簽到並記住在此裝置", use_container_width=True, type="primary")

# --- 3. 核心簽到邏輯 ---
def run_punch(u, p):
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
            return False, "❌ 登入失敗"
        
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        payload_p.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })
        ajax_headers = {"X-MicrosoftAjax": "Delta=true", "X-Requested-With": "XMLHttpRequest", "Referer": PUNCH_URL}
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        if "簽到完成" in response.text:
            return True, "🎉 簽到成功！"
        return False, "⚠️ 簽到未成功"
    except Exception as e:
        return False, f"💥 錯誤: {str(e)}"

# --- 4. 點擊執行與存入 Cookie ---
if submit_btn:
    if u_id and u_pw:
        # 存入 Cookie，設定過期時間為 30 天後
        cookie_manager.set("u_id", u_id, expires_at=datetime.now() + timedelta(days=30))
        cookie_manager.set("u_pw", u_pw, expires_at=datetime.now() + timedelta(days=30))
        
        with st.spinner("連線中..."):
            success, msg = run_punch(u_id, u_pw)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)
    else:
        st.warning("請完整輸入資訊。")