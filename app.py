import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- 頁面配置 ---
st.set_page_config(page_title="USUN 快速簽到系統", page_icon="📝", layout="centered")

# --- 1. 初始化記憶功能 (從 Session 讀取) ---
# 這裡模擬記憶功能，只要在同一個瀏覽器週期內，資訊就會留著
if 'saved_user_id' not in st.session_state:
    st.session_state.saved_user_id = ""
if 'saved_user_pw' not in st.session_state:
    st.session_state.saved_user_pw = ""

st.title("📝 USUN 線上簽到系統")
st.markdown("---")

# --- 2. 主頁面登入表單 ---
with st.container():
    st.subheader("🔐 員工登入")
    
    # 直接將 session_state 的值賦予給 value，達成「一開頁面就顯示」
    u_id = st.text_input("工號", value=st.session_state.saved_user_id, placeholder="請輸入工號")
    u_pw = st.text_input("密碼", type="password", value=st.session_state.saved_user_pw, placeholder="請輸入密碼")
    
    st.write("") 
    # 注意：這裡不使用 st.form，因為 st.form 會在提交前阻擋 state 更新
    submit_btn = st.button("🚀 執行簽到並記住我", use_container_width=True, type="primary")

# --- 3. 核心簽到邏輯 (簡化版) ---
def run_punch(u, p):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    try:
        # 登入
        res_l = session.get(LOGIN_URL)
        soup_l = BeautifulSoup(res_l.text, 'html.parser')
        payload_l = {tag.get('name'): tag.get('value', '') for tag in soup_l.find_all('input') if tag.get('name')}
        payload_l.update({"ctl00$ContentPlaceHolder1$txtLogin": u, "ctl00$ContentPlaceHolder1$txtPass": p, "ctl00$ContentPlaceHolder1$btn_login": "登入"})
        login_res = session.post(LOGIN_URL, data=payload_l)
        
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：帳密錯誤。"

        # 簽到
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
            time_m = re.search(r'lb_time".*?>(.*?)</span>', response.text)
            return True, f"🎉 簽到成功！時間：{time_m.group(1) if time_m else '已記錄'}"
        return False, "⚠️ 簽到未成功。"

    except Exception as e:
        return False, f"💥 錯誤: {str(e)}"

# --- 4. 執行與記憶動作 ---
if submit_btn:
    if u_id and u_pw:
        # 關鍵：點擊後立刻將資訊存入 session_state
        st.session_state.saved_user_id = u_id
        st.session_state.saved_user_pw = u_pw
        
        with st.spinner("通訊中..."):
            success, msg = run_punch(u_id, u_pw)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)
    else:
        st.warning("請輸入帳密。")