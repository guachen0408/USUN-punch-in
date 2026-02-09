import streamlit as st
st.set_page_config(page_title="USUN 智慧打卡助手", page_icon="📝", layout="centered")

import requests
from bs4 import BeautifulSoup
import re
import extra_streamlit_components as stx
import time
import json
from datetime import datetime, timedelta
from typing import Tuple, Dict

# --- 常數與設定 ---
BASE_URL = "https://usun-hrm.usuntek.com"
LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
DEFAULT_TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
}

# --- 核心內部函數 ---

def _get_form_payload(html: str) -> Dict[str, str]:
    """從 HTML 中提取所有 input 表單欄位"""
    soup = BeautifulSoup(html, 'html.parser')
    return {tag.get('name'): tag.get('value', '') for tag in soup.find_all('input') if tag.get('name')}

def _handle_debug_info(title: str, response: requests.Response, session: requests.Session):
    """在 UI 中顯示詳細的調試資訊"""
    with st.expander(f"🔍 {title}"):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**請求/會話資訊：**")
            st.code(json.dumps({
                "URL": response.url,
                "Headers": dict(session.headers),
                "Cookies": dict(session.cookies)
            }, indent=2, ensure_ascii=False))
        with col2:
            st.write("**回應狀態：**")
            st.code(f"狀態碼：{response.status_code}\n回應時間：{response.elapsed.total_seconds():.2f}秒\n內容長度：{len(response.text)} 字元")
        
        st.write("**回應內容示範 (前 1000 字)：**")
        st.code(response.text[:1000])

def run_punch(u: str, p: str, debug: bool = False) -> Tuple[bool, str]:
    """執行自動打卡主流程
    
    Args:
        u: 工號
        p: 密碼
        debug: 是否顯示詳細調試資訊
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # ===== 步驟 1：獲取登入頁面與 Token =====
        with st.spinner("📡 步驟 1/3 - 正在連線至系統..."):
            res_l = session.get(LOGIN_URL, timeout=DEFAULT_TIMEOUT)
            if debug:
                _handle_debug_info("[第1步] GET Login Page", res_l, session)
            
            payload_l = _get_form_payload(res_l.text)
            if not payload_l:
                return False, "❌ 無法提取登入表單結構，可能是系統維護或頁面更新。"

        # 更新登入認證
        payload_l.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u, 
            "ctl00$ContentPlaceHolder1$txtPass": p, 
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })

        # ===== 步驟 2：提交認證 =====
        with st.spinner("📡 步驟 2/3 - 正在提交身份驗證..."):
            login_res = session.post(LOGIN_URL, data=payload_l, timeout=DEFAULT_TIMEOUT)
            if debug:
                _handle_debug_info("[第2步] POST Login Auth", login_res, session)
            
            # 檢查登入是否失敗（通常沒跳轉就是失敗）
            if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
                return False, "❌ 登入失敗：帳號或密碼錯誤，或是伺服器拒絕存取。"

        # ===== 步驟 3：執行打卡動作 =====
        with st.spinner("📡 步驟 3/3 - 正在發送打卡請求..."):
            res_p = session.get(PUNCH_URL, timeout=DEFAULT_TIMEOUT)
            payload_p = _get_form_payload(res_p.text)
            
            if not payload_p:
                return False, "⚠️ 身份驗證似乎已過期，無法進入打卡頁面。"

            payload_p.update({
                "ctl00$RadScriptManager1": "ctl00$ContentPlaceHolder1$ctl00$ContentPlaceHolder1$RadAjaxPanel1Panel|ctl00$ContentPlaceHolder1$btnSubmit_input",
                "__EVENTTARGET": "ctl00$ContentPlaceHolder1$btnSubmit_input",
                "__EVENTARGUMENT": "",
                "__ASYNCPOST": "true",
                "ctl00$ContentPlaceHolder1$btnSubmit_input": "確認送出"
            })

            ajax_headers = {
                "X-MicrosoftAjax": "Delta=true",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": PUNCH_URL,
                "Origin": BASE_URL,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            
            response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers, timeout=DEFAULT_TIMEOUT)
            if debug:
                _handle_debug_info("[第3步] POST Punch Request", response, session)

        # ===== 結果解析 =====
        if "簽到完成" in response.text:
            return True, "🎉 簽到完成！伺服器已成功記錄資訊。"
        else:
            # 嘗試從回應中提取錯誤訊息（提取中文字元）
            error_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"⚠️ 伺服器回應：{error_msg if error_msg else '請求被拒絕，可能已重複簽到'}"

    except requests.exceptions.Timeout:
        return False, "⏱️ 連線逾時：伺服器反應緩慢，請稍後再試。"
    except requests.exceptions.ConnectionError:
        return False, "🔌 網路連線失敗：請檢查您的網路或 VPN 連線。"
    except Exception as e:
        return False, f"💥 未知異常：{str(e)}"


# --- 頁面樣式 ---

st.title("📝 USUN 智慧簽到助手")
st.markdown("""
<style>
    /* 主體背景 */
    .main {
        background-color: #f8f9fa;
    }
    /* 按鈕樣式 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
    }
    /* 輸入框樣式 */
    .stTextInput>div>div>input {
        border-radius: 8px;
    }
    /* 深色模式支援 */
    @media (prefers-color-scheme: dark) {
        .main {
            background-color: #0e1117;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化設定 ---
cookie_manager = stx.CookieManager(key="punch_cookie_manager")
all_cookies = cookie_manager.get_all()
saved_id = all_cookies.get("u_id", "")
saved_pw = all_cookies.get("u_pw", "")


st.info("💡 **提示：** 系統會自動記住您的登入資訊 30 天，讓您下次簽到更迅速。")

# 建立置中的表單佈局
col_a, col_b, col_c = st.columns([1, 2, 1])

with col_b:
    st.subheader("🔐 員工身份驗證")
    u_id = st.text_input("工號", value=saved_id, placeholder="例如：E12345", key="id_input")
    u_pw = st.text_input("密碼", type="password", value=saved_pw, placeholder="請輸入 HRM 密碼", key="pw_input")

    # 進階選項
    with st.expander("🛠️ 進階設定"):
        debug_mode = st.checkbox("🔍 啟用連線調試模式", value=False, help="若簽到異常，開啟此模式可查看詳細錯誤資訊。")

    st.markdown("---")
    
    col_l, col_r = st.columns(2)
    with col_l:
        submit_btn = st.button("🚀 立即簽到", type="primary")
    with col_r:
        help_btn = st.button("❓ 常見問題")

if help_btn:
    st.toast("正在載入說明...", icon="ℹ️")
    st.info(
        "**📚 使用指南：**\n\n"
        "1. **帳號密碼**：請使用與 HRM 系統相同的憑證。\n"
        "2. **連線問題**：若人在公司外，請務必先透過 VPN 連線至公司內網。\n"
        "3. **保存資訊**：首次成功後會自動儲存，免重複輸入。\n"
        "4. **客服聯絡**：若發生系統異常，請截圖調試資訊傳送至 IT-Support@usuntek.com"
    )

# --- 打卡邏輯處理 ---
if "submit_pending" not in st.session_state:
    st.session_state.submit_pending = False

if submit_btn:
    st.session_state.submit_pending = True

if st.session_state.submit_pending:
    if not u_id or not u_pw:
        st.warning("⚠️ 請完整填寫工號與密碼。")
        st.session_state.submit_pending = False
    else:
        # 儲存 Cookie
        expiry = datetime.now() + timedelta(days=30)
        cookie_manager.set("u_id", u_id, expires_at=expiry, key="set_uid")
        cookie_manager.set("u_pw", u_pw, expires_at=expiry, key="set_upw")
        
        # 執行主流程 (使用 st.status 包裝以提供更好回饋)
        with st.status("正在執行打卡程序...", expanded=True) as status:
            success, msg = run_punch(u_id, u_pw, debug=debug_mode)
            if success:
                status.update(label="✅ 簽到成功", state="complete")
                st.success(msg)
                st.balloons()
                st.toast("簽到完成！", icon="🎉")
            else:
                status.update(label="❌ 簽到失敗", state="error")
                st.error(msg)
                with st.expander("💡 快速排錯建議"):
                    st.markdown(
                        "1. **檢查密碼**：請確認密碼是否剛更新？\n"
                        "2. **檢查網路**：您是否已連上 VPN？\n"
                        "3. **重複簽到**：系統可能已經有您今天的打卡記錄了。\n"
                        "4. **手動確認**：[點此前往 HRM 官網確認](https://usun-hrm.usuntek.com)"
                    )
        
        # 完成後重設狀態
        st.session_state.submit_pending = False

# 頁尾
st.markdown("---")
st.caption("© 2026 USUN Technology | 智慧打卡助手 v2.0")
