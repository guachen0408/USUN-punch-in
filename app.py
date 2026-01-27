import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- 頁面配置：移除側欄，主畫面居中 ---
st.set_page_config(page_title="USUN 個人簽到系統", page_icon="📝", layout="centered")

st.title("📝 USUN 個人簽到系統")
st.markdown("---")

# --- 1. 登入表單：利用標準 Form 觸發瀏覽器各自記憶 ---
# 透過 st.form，瀏覽器會將此視為正式登入頁面，自動彈出「儲存密碼」詢問
with st.form("personal_login_form"):
    st.subheader("🔐 員工登入")
    st.write("請輸入資訊，簽到成功後瀏覽器將詢問是否記憶此裝置的帳密。")
    
    u_id = st.text_input("工號", placeholder="例如: 12345")
    u_pw = st.text_input("密碼", type="password", placeholder="請輸入密碼")
    
    st.write("")
    # 送出按鈕
    submit_btn = st.form_submit_button("🚀 執行簽到", use_container_width=True, type="primary")

st.info("💡 提示：本系統不會在伺服器儲存您的帳密。資料將由您的瀏覽器（如 Chrome, Safari）安全管理。")

# --- 2. 核心簽到邏輯 (不帶座標版) ---
def run_punch(u, p):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    try:
        # 登入流程
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
            return False, "❌ 登入失敗：請確認工號與密碼。"

        # 簽到封包
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
            return True, f"🎉 簽到完成！\n\n系統紀錄時間：{time_m.group(1) if time_m else '剛才'}"
        else:
            clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"⚠️ 簽到未成功：{clean_msg if clean_msg else '請檢查帳密'}"

    except Exception as e:
        return False, f"💥 通訊異常: {str(e)}"

# --- 3. 執行動作 ---
if submit_btn:
    if not u_id or not u_pw:
        st.warning("請填寫完整帳號密碼。")
    else:
        with st.spinner("連線中..."):
            success, msg = run_punch(u_id, u_pw)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)