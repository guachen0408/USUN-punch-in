import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="USUN 快速簽到系統", page_icon="📝")

# --- 初始化與自動填入 (觸發瀏覽器記憶) ---
with st.sidebar:
    st.header("🔐 員工登入")
    with st.form("login_form"):
        u_id = st.text_input("工號", key="user_id")
        u_pw = st.text_input("密碼", type="password", key="user_pw")
        st.caption("💡 瀏覽器將在點擊後詢問是否儲存資訊。")
        submit_btn = st.form_submit_button("🚀 執行簽到", use_container_width=True)

st.title("📝 USUN 線上簽到系統")
st.info("模式：已移除座標傳輸。系統將以伺服器端接收時間與您的連線 IP 為準。")

# --- 核心簽到邏輯 (不帶座標版) ---
def run_punch_no_geo(u, p):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    # 模擬標準瀏覽器，這是穩定簽到的關鍵
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

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
        
        # 判斷是否登入成功 (未被彈回 Login 頁)
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：請確認帳號密碼。"

        # 2. 準備簽到封包 (獲取 ViewState)
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        
        # 3. 發送簽到指令 (拿掉 longitude 與 latitude)
        payload_p.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            # 注意：此處已移除經緯度欄位
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })

        ajax_headers = {
            "X-MicrosoftAjax": "Delta=true", 
            "X-Requested-With": "XMLHttpRequest", 
            "Referer": PUNCH_URL
        }
        
        # 發送最終 Ajax 請求
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        
        # 4. 解析回傳訊息 (針對你提供的 3591 字元封包結構)
        if "簽到完成" in response.text:
            time_m = re.search(r'lb_time".*?>(.*?)</span>', response.text)
            name_m = re.search(r'lbName".*?>(.*?)</span>', response.text)
            u_name = name_m.group(1) if name_m else "員工"
            p_time = time_m.group(1) if time_m else "伺服器已記錄"
            return True, f"🎉 {u_name}，簽到成功！\n\n系統紀錄時間：{p_time}"
        else:
            # 提取錯誤文字 (例如: 已簽到過、連線逾時)
            clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"⚠️ 簽到未成功。系統回應：{clean_msg}"

    except Exception as e:
        return False, f"💥 通訊異常: {str(e)}"

# --- 點擊動作 ---
if submit_btn:
    if not u_id or not u_pw:
        st.warning("請在側邊欄輸入帳號密碼。")
    else:
        with st.spinner("正在與 USUN 伺服器同步資訊..."):
            success, msg = run_punch_no_geo(u_id, u_pw)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)