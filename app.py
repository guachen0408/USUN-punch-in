import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

# 設定網頁標題
st.set_page_config(page_title="公司自動打卡系統", page_icon="⏰")
st.title("🚀 公司自動打卡工具")

# --- 使用者輸入區 ---
st.sidebar.header("設定憑據")
username = st.sidebar.text_input("員工帳號")
password = st.sidebar.text_input("登入密碼", type="password")

st.sidebar.header("地理位置")
lat = st.sidebar.text_input("緯度 (Latitude)", value="25.054495717723004")
lon = st.sidebar.text_input("經度 (Longitude)", value="121.19719822332199")

# --- 打卡邏輯函數 (從 punch.py 移植) ---
def start_punch(u, p, la, lo):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."})
    
    try:
        # 1. 登入
        res_page = session.get(LOGIN_URL)
        soup = BeautifulSoup(res_page.text, 'html.parser')
        
        # 獲取 ASP.NET 隱藏欄位
        def get_fields(s):
            return {f: s.find('input', {'id': f})['value'] for f in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"] if s.find('input', {'id': f})}

        payload = get_fields(soup)
        payload.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u,
            "ctl00$ContentPlaceHolder1$txtPass": p,
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })
        
        login_res = session.post(LOGIN_URL, data=payload, allow_redirects=True)
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "登入失敗，請檢查帳號密碼。"

        # 2. 打卡
        punch_page = session.get(PUNCH_URL)
        p_soup = BeautifulSoup(punch_page.text, 'html.parser')
        p_payload = get_fields(p_soup)
        p_payload.update({
            "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$longitude": lo,
            "ctl00$ContentPlaceHolder1$latitude": la,
            "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
        })
        
        headers = {"X-MicrosoftAjax": "Delta=true", "Referer": PUNCH_URL}
        resp = session.post(PUNCH_URL, data=p_payload, headers=headers)
        
        if "成功" in resp.text:
            return True, "打卡成功！"
        else:
            return False, f"伺服器回應異常: {resp.text[:100]}"
            
    except Exception as e:
        return False, f"發生錯誤: {str(e)}"

# --- 介面按鈕 ---
if st.button("立即執行打卡"):
    if not username or not password:
        st.error("請先輸入帳號與密碼！")
    else:
        with st.spinner('連線中，請稍候...'):
            success, msg = start_punch(username, password, lat, lon)
            if success:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)