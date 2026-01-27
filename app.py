import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# 設定網頁介面
st.set_page_config(page_title="USUN 簽到系統", page_icon="✅")
st.title("✅ USUN 線上簽到工具")
st.markdown("請輸入員工資訊。成功後將自動顯示系統記錄的時間。")

# --- 側邊欄設定 ---
st.sidebar.header("🔐 憑據設定")
u_id = st.sidebar.text_input("帳號 (User ID)")
u_pw = st.sidebar.text_input("密碼 (Password)", type="password")

st.sidebar.header("🌐 座標設定")
lat = st.sidebar.text_input("緯度", value="25.0544957")
lon = st.sidebar.text_input("經度", value="121.1971982")

# --- 核心邏輯 ---
def run_punch(u, p, la, lo):
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        # 1. 登入
        res_l = session.get(LOGIN_URL)
        soup_l = BeautifulSoup(res_l.text, 'html.parser')
        
        # 提取隱藏欄位與帳密對接
        payload_l = {tag.get('name'): tag.get('value', '') for tag in soup_l.find_all('input') if tag.get('name')}
        payload_l.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u,
            "ctl00$ContentPlaceHolder1$txtPass": p,
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })
        
        login_res = session.post(LOGIN_URL, data=payload_l, allow_redirects=True)
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            return False, "❌ 登入失敗：請確認帳號密碼。"

        # 2. 獲取打卡頁 ViewState
        res_p = session.get(PUNCH_URL)
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        
        # 3. 發送打卡封包
        payload_p.update({
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

        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers)
        raw_res = response.text

        # 4. 解析回傳的 3591 字元 (精準匹配你的封包)
        if "簽到完成" in raw_res or "簽到資訊" in raw_res:
            # 抓取姓名
            name_m = re.search(r'lbName".*?>(.*?)</span>', raw_res)
            # 抓取系統紀錄時間
            time_m = re.search(r'lb_time".*?>(.*?)</span>', raw_res)
            
            user_name = name_m.group(1) if name_m else "員工"
            punch_time = time_m.group(1) if time_m else "剛才"
            return True, f"🎉 簽到成功！\n\n**姓名**：{user_name}\n\n**系統紀錄時間**：{punch_time}"
        
        elif "pageRedirect" in raw_res:
            return False, "⚠️ 失敗：Session 過期或被強制跳轉。"
        else:
            # 抓取回傳的中文字做錯誤提示
            clean_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', raw_res))
            return False, f"⚠️ 系統提示：{clean_msg if clean_msg else '未知的狀態'}"

    except Exception as e:
        return False, f"💥 崩潰錯誤: {str(e)}"

# --- UI 介面 ---
if st.button("🚀 執行簽到", use_container_width=True):
    if not u_id or not u_pw:
        st.error("請輸入帳號密碼。")
    else:
        with st.spinner('正在與公司伺服器通訊...'):
            success, message = run_punch(u_id, u_pw, lat, lon)
            if success:
                st.success(message)
                st.balloons()
            else:
                st.error(message)