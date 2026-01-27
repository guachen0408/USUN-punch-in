import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- 頁面配置 ---
st.set_page_config(page_title="USUN 快速簽到系統", page_icon="📝", layout="centered")

# --- 初始化 Session State (記憶工號) ---
if 'remember_id' not in st.session_state:
    st.session_state.remember_id = ""

st.title("📝 USUN 線上簽到系統")
st.markdown("---")

# --- 主頁面登入表單 ---
# 使用 st.form 可以觸發瀏覽器的自動填入與記憶密碼功能
with st.form("main_punch_form"):
    st.subheader("🔐 員工登入")
    
    # 使用之前儲存的工號作為預設值
    u_id = st.text_input("工號", value=st.session_state.remember_id, placeholder="請輸入您的工號")
    u_pw = st.text_input("密碼", type="password", placeholder="請輸入您的密碼")
    
    st.write("") # 增加間距
    submit_btn = st.form_submit_button("🚀 執行簽到", use_container_width=True, type="primary")

st.info("💡 模式：純帳密驗證。點擊簽到後，瀏覽器通常會詢問是否儲存此密碼。")

# --- 核心簽到邏輯 (不帶座標) ---
def run_punch(u, p):
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
        payload_l.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u, 
            "ctl00$ContentPlaceHolder1$txtPass": p, 
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })
        login_res = session.post(LOGIN_URL, data=payload_l)
        
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：請確認帳號密碼。"

        # 2. 獲取打卡頁 ViewState
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        
        # 3. 發送簽到指令
        payload_p.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })

        ajax_headers = {"X-MicrosoftAjax": "Delta=true", "X-Requested-With": "XMLHttpRequest", "Referer": PUNCH_URL}
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        
        # 4. 解析回傳訊息 (針對 3591 字元結構)
        if "簽到完成" in response.text:
            time_m = re.search(r'lb_time".*?>(.*?)</span>', response.text)
            name_m = re.search(r'lbName".*?>(.*?)</span>', response.text)
            u_name = name_m.group(1) if name_m else "員工"
            p_time = time_m.group(1) if time_m else "伺服器已記錄"
            return True, f"🎉 {u_name}，簽到成功！\n\n系統紀錄時間：{p_time}"
        else:
            clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"⚠️ 失敗：{clean_msg if clean_msg else '請檢查帳密或伺服器狀態'}"

    except Exception as e:
        return False, f"💥 通訊異常: {str(e)}"

# --- 執行動作 ---
if submit_btn:
    if not u_id or not u_pw:
        st.warning("請完整填寫工號與密碼。")
    else:
        # 儲存工號到 session_state 供下次預填
        st.session_state.remember_id = u_id
        
        with st.spinner("同步簽到資訊中..."):
            success, msg = run_punch(u_id, u_pw)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)