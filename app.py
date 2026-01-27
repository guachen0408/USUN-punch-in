import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
# ... 其他 requests, BeautifulSoup 引用保持不變 ...

st.set_page_config(page_title="USUN 記憶簽到", page_icon="📝", layout="centered")

# --- 1. 初始化 Cookie 管理器 ---
cookie_manager = stx.CookieManager(key="cookie_manager")

# --- 2. 讀取 Cookie (強化邏輯) ---
# 使用 cookie_manager.get_all() 有助於更穩定地抓取所有資訊
cookies = cookie_manager.get_all()

# 從 cookies 字典中抓取，若無則為空字串
saved_id = cookies.get("u_id", "")
saved_pw = cookies.get("u_pw", "")

st.title("📝 USUN 個人簽到系統")
st.markdown("---")

st.subheader("🔐 員工登入")

# 使用 key 參數讓欄位狀態更穩定
u_id = st.text_input("工號", value=saved_id, placeholder="請輸入工號", key="input_id")
u_pw = st.text_input("密碼", type="password", value=saved_pw, placeholder="請輸入密碼", key="input_pw")

submit_btn = st.button("🚀 執行簽到並記住在此裝置", use_container_width=True, type="primary")

# --- 3. 點擊執行並存入 Cookie ---
if submit_btn:
    if u_id and u_pw:
        # 存入 Cookie
        # 增加 expires_at 確保長效性
        expire_date = datetime.now() + timedelta(days=30)
        cookie_manager.set("u_id", u_id, expires_at=expire_date, key="set_id")
        cookie_manager.set("u_pw", u_pw, expires_at=expire_date, key="set_pw")
        
        # 執行原本的 run_punch 函數內容...
        # ...
        st.success("資訊已更新至本機 Cookie，下次開啟將自動預填。")
    else:
        st.warning("請完整輸入資訊。")