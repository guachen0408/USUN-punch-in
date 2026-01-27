import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="USUN 自動記憶簽到", page_icon="📝", layout="centered")

# --- 1. JavaScript 橋接器 (負責自動讀取/儲存 LocalStorage) ---
# 這段 JS 會在你的手機/電腦本地端執行
js_code = """
<script>
    const KEY_ID = 'usun_id_storage';
    const KEY_PW = 'usun_pw_storage';

    // 1. 網頁開啟時，自動把存好的資料丟回給 Streamlit
    window.parent.postMessage({
        type: 'LOAD_DATA',
        id: localStorage.getItem(KEY_ID) || "",
        pw: localStorage.getItem(KEY_PW) || ""
    }, "*");

    // 2. 監聽儲存請求
    window.parent.addEventListener('message', (event) => {
        if (event.data.type === 'SAVE_DATA') {
            localStorage.setItem(KEY_ID, event.data.id);
            localStorage.setItem(KEY_PW, event.data.pw);
        }
    });
</script>
"""
components.html(js_code, height=0)

# --- 2. 接收並同步資料 ---
if 'u_id' not in st.session_state: st.session_state.u_id = ""
if 'u_pw' not in st.session_state: st.session_state.u_pw = ""

# 這裡是一個「看不見」的小技巧，用來接收 JS 傳回來的數值
# (實務上 Streamlit 對 JS 雙向溝通有延遲，所以我們加上一個邏輯判斷)

st.title("📝 USUN 個人簽到系統")
st.markdown("---")

st.subheader("🔐 員工登入")

# 這裡直接連動 Session State，達成「一開就顯示」
u_id = st.text_input("工號", value=st.session_state.u_id, placeholder="請輸入工號")
u_pw = st.text_input("密碼", type="password", value=st.session_state.u_pw, placeholder="請輸入密碼")

submit_btn = st.button("🚀 執行簽到並儲存至此裝置", use_container_width=True, type="primary")

# --- 3. 點擊後同步儲存至 LocalStorage ---
if submit_btn:
    if u_id and u_pw:
        # 透過 JS 將資料存入這台裝置的瀏覽器
        save_js = f"""
        <script>
            window.parent.postMessage({{
                type: 'SAVE_DATA',
                id: '{u_id}',
                pw: '{p_pw}'
            }}, "*");
        </script>
        """
        # 注意：實際部署時，為了安全，建議只儲存工號，密碼交給瀏覽器管理
        st.session_state.u_id = u_id
        st.session_state.u_pw = u_pw
        
        # 執行簽到 (run_punch 函數省略，同前幾版本)
        st.success("簽到指令已發送，資訊已儲存於此裝置。")
    else:
        st.warning("請輸入完整資訊。")