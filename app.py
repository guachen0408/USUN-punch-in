import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import extra_streamlit_components as stx
from datetime import datetime, timedelta

st.set_page_config(page_title="USUN 穩定記憶版", page_icon="📝", layout="centered")

# --- 1. 初始化 Cookie 管理器 ---
# 增加 key 確保元件唯一性
cookie_manager = stx.CookieManager(key="stable_cookie_manager")

# --- 2. 核心記憶邏輯：緩衝讀取 ---
# 優先從 session_state 讀取，若無則嘗試從 Cookie 抓
if 'u_id' not in st.session_state:
    st.session_state.u_id = ""
if 'u_pw' not in st.session_state:
    st.session_state.u_pw = ""

# 抓取所有 Cookie
all_cookies = cookie_manager.get_all()

# 只有在 Cookie 有值且 session_state 為空時才更新 (避免覆蓋)
if all_cookies:
    if not st.session_state.u_id and "u_id" in all_cookies:
        st.session_state.u_id = all_cookies["u_id"]
    if not st.session_state.u_pw and "u_pw" in all_cookies:
        st.session_state.u_pw = all_cookies["u_pw"]

st.title("📝 USUN 個人簽到系統")
st.markdown("---")

# --- 3. 介面呈現 ---
st.subheader("🔐 員工登入")

# 使用存放在 session_state 中的值，這樣即使 Cookie 載入慢，也不會閃退成空白
u_id = st.text_input("工號", value=st.session_state.u_id, placeholder="請輸入工號", key="id_input")
u_pw = st.text_input("密碼", type="password", value=st.session_state.u_pw, placeholder="請輸入密碼", key="pw_input")

submit_btn = st.button("🚀 執行簽到並記住在此裝置", use_container_width=True, type="primary")

# --- 4. 點擊執行並強制更新 Cookie ---
if submit_btn:
    if u_id and u_pw:
        # 1. 更新當前狀態
        st.session_state.u_id = u_id
        st.session_state.u_pw = u_pw
        
        # 2. 強制寫入 Cookie (設定 30 天)
        in_30_days = datetime.now() + timedelta(days=30)
        cookie_manager.set("u_id", u_id, expires_at=in_30_days)
        cookie_manager.set("u_pw", u_pw, expires_at=in_30_days)
        
        # 3. 執行原本的 run_punch 函數邏輯 (略)
        st.toast("資訊已強制寫入本機 Cookie")
        # (這裡接 run_punch 邏輯...)
    else:
        st.warning("請輸入完整資訊。")