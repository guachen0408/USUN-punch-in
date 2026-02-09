import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import extra_streamlit_components as stx
import socket
import time
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="USUN 記憶簽到", page_icon="📝", layout="centered")

# --- 核心函數 ---
def run_punch(u, p, debug=False):
    """正常模式：連接真實 HRM 系統
    
    Args:
        u: 工號
        p: 密碼
        debug: 是否顯示詳細的網路封包信息
    """
    BASE_URL = "https://usun-hrm.usuntek.com"
    LOGIN_URL = f"{BASE_URL}/Ez-Portal/Login.aspx"
    PUNCH_URL = f"{BASE_URL}/Ez-Portal/Employee/PunchOutBaiDu.aspx"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    })

    try:
        # ===== 第 1 步：獲取登入頁面 =====
        st.write("📡 步驟 1/3 - 連線到登入頁面...")
        res_l = session.get(LOGIN_URL, timeout=10)
        
        if debug:
            with st.expander("🔍 [第1步] GET " + LOGIN_URL):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**請求頭：**")
                    st.code(json.dumps(dict(session.headers), indent=2, ensure_ascii=False))
                with col2:
                    st.write("**回應狀態：**")
                    st.code(f"狀態碼：{res_l.status_code}\n回應時間：{res_l.elapsed.total_seconds():.2f}秒\n" + 
                           f"內容長度：{len(res_l.text)} 字元")
                st.write("**回應頭示範：**")
                st.code(json.dumps(dict(list(res_l.headers.items())[:5]), indent=2, ensure_ascii=False))
        
        st.write("✅ 連線成功，開始驗證認證...")
        
        soup_l = BeautifulSoup(res_l.text, 'html.parser')
        payload_l = {tag.get('name'): tag.get('value', '') for tag in soup_l.find_all('input') if tag.get('name')}
        
        # 顯示調試信息（當表單為空時）
        if not payload_l:
            st.warning("⚠️ 無法從登入頁面提取表單字段。")
            st.write("💡 可能原因：")
            st.write("  • HRM 系統頁面結構已更新")
            st.write("  • 伺服器返回非 HTML 內容")
            with st.expander("🔍 查看回應內容"):
                st.code(res_l.text[:1000], language="html")
            return False, "❌ 無法提取登入表單，請聯絡 IT 部門。"
        
        st.write(f"📋 提取表單字段數：{len(payload_l)}")
        
        if debug:
            with st.expander("📋 第 1 步 - 表單字段"):
                st.write("**提取的表單字段：**")
                for key, val in list(payload_l.items())[:10]:  # 只顯示前 10 個
                    st.code(f"{key} = {val[:50] if val else '(空)'}")
        
        # 更新登入認證
        payload_l.update({
            "ctl00$ContentPlaceHolder1$txtLogin": u, 
            "ctl00$ContentPlaceHolder1$txtPass": p, 
            "ctl00$ContentPlaceHolder1$btn_login": "登入"
        })
        
        # ===== 第 2 步：提交登入 =====
        st.write("📡 步驟 2/3 - 提交登入認證...")
        st.write(f"   • 工號：{u}")
        st.write(f"   • 傳送 {len(payload_l)} 個表單欄位...")
        
        login_res = session.post(LOGIN_URL, data=payload_l, timeout=10)
        st.write(f"   • 回應狀態碼：{login_res.status_code}")
        st.write(f"   • 最終 URL：{login_res.url}")
        st.write(f"   • 回應時間：{login_res.elapsed.total_seconds():.2f}秒")
        
        if debug:
            with st.expander("🔍 [第2步] POST " + LOGIN_URL + " - 詳細信息"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**請求方法：**")
                    st.code("POST")
                    st.write("**傳送的表單欄位數：**")
                    st.code(str(len(payload_l)))
                
                with col2:
                    st.write("**回應狀態：**")
                    st.code(f"{login_res.status_code}")
                    st.write("**最終 URL：**")
                    st.code(login_res.url)
                
                with col3:
                    st.write("**Cookies：**")
                    cookies_str = "\n".join([f"{k}={v[:30]}" for k, v in session.cookies.items()])
                    st.code(cookies_str if cookies_str else "(無)")
                
                st.write("**表單欄位示範（前 5 個）：**")
                payload_display = {k: v[:50] if v else "(空)" for k, v in list(payload_l.items())[:5]}
                st.code(json.dumps(payload_display, indent=2, ensure_ascii=False))
                
                st.write("**回應內容示範（前 500 字）：**")
                st.code(login_res.text[:500])
        
        # 檢查登入是否失敗
        if "Login.aspx" in login_res.url and "ReturnUrl" not in login_res.url:
            st.error("❌ 登入失敗 - 伺服器未跳轉到授權頁面")
            if debug:
                st.write("**診斷：** 回應 URL 中仍包含 Login.aspx 且無 ReturnUrl，表示登入未成功")
            return False, "❌ 登入失敗：帳號或密碼錯誤，或伺服器拒絕登入。"
        
        st.write("✅ 身份認證成功，啟動打卡程序...")

        # ===== 第 3 步：發送打卡請求 =====
        st.write("📡 步驟 3/3 - 發送打卡請求...")
        res_p = session.get(PUNCH_URL, timeout=10)
        
        if debug:
            with st.expander("🔍 [第3步-GET] " + PUNCH_URL):
                st.write(f"**狀態碼：** {res_p.status_code}")
                st.write(f"**回應時間：** {res_p.elapsed.total_seconds():.2f}秒")
                st.write("**回應內容示範（前 500 字）：**")
                st.code(res_p.text[:500])
        
        soup_p = BeautifulSoup(res_p.text, 'html.parser')
        payload_p = {tag.get('name'): tag.get('value', '') for tag in soup_p.find_all('input') if tag.get('name')}
        
        if not payload_p:
            return False, "⚠️ 無法提取打卡頁面表單。"
        
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
        
        response = session.post(PUNCH_URL, data=payload_p, headers=ajax_headers, timeout=10)
        st.write("✅ 伺服器已收到打卡請求，正在處理...")
        
        if debug:
            with st.expander("🔍 [第3步-POST] " + PUNCH_URL + " (Ajax)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Ajax 請求頭：**")
                    ajax_headers_display = {k: v for k, v in ajax_headers.items() if k != "Authorization"}
                    st.code(json.dumps(ajax_headers_display, indent=2, ensure_ascii=False))
                
                with col2:
                    st.write("**回應狀態：**")
                    st.code(f"狀態碼：{response.status_code}\n回應時間：{response.elapsed.total_seconds():.2f}秒")
                
                st.write("**回應內容（前 1000 字）：**")
                st.code(response.text[:1000])
        
        # 檢查回傳內容
        if "簽到完成" in response.text:
            return True, "🎉 簽到完成！伺服器已成功記錄。"
        else:
            error_msg = "".join(re.findall(r'[\u4e00-\u9fa5]+', response.text))
            return False, f"⚠️ 失敗：{error_msg if error_msg else '封包被拒絕，請檢查是否已簽到過'}"

    except requests.exceptions.Timeout:
        return False, "⏱️ 連線逾時 (10秒無回應)：伺服器沒有回應，請使用診斷工具檢查網路。"
    except requests.exceptions.ConnectionError:
        return False, "🔌 網路連線失敗：無法連線到打卡系統。請使用 🔧 診斷工具 檢查網路設定。"
    except Exception as e:
        return False, f"💥 通訊異常: {str(e)}"


# --- 初始化設定 ---
cookie_manager = stx.CookieManager(key="punch_cookie_manager")
all_cookies = cookie_manager.get_all()
saved_id = all_cookies.get("u_id", "")
saved_pw = all_cookies.get("u_pw", "")

# --- 模式設定 (固定為正常模式) ---
mode = "🚀 正常模式 (生產)"



# ============ 正常模式 ============
st.title("📝 USUN 個人簽到系統")
st.markdown("---")

st.subheader("🔐 員工登入")
u_id = st.text_input("工號", value=saved_id, placeholder="請輸入工號", key="id_input")
u_pw = st.text_input("密碼", type="password", value=saved_pw, placeholder="請輸入密碼", key="pw_input")

# 調試模式開關
debug_mode = st.checkbox("🔍 啟用調試模式 (顯示詳細網路封包)", value=False)
if debug_mode:
    st.info("ℹ️ 調試模式已啟用 - 將顯示所有 HTTP 請求/回應的詳細信息，幫助診斷登入問題。")

col1, col2 = st.columns(2)
with col1:
    submit_btn = st.button("🚀 執行簽到", use_container_width=True, type="primary")
with col2:
    if st.button("❓ 需要幫助？", use_container_width=True):
        st.info(
            "**遇到問題？**\n\n"
            "1️⃣ **無法連接** → 請檢查網路或 VPN\n"
            "2️⃣ **需更多信息** → 展開下方「使用說明」"
        )

with st.expander("📖 使用說明"):
    st.markdown(
        "**功能介紹：**\n\n"
        "🚀 **正常模式** - 連接真實 HRM 系統\n"
        "  • 需要網路連接正常\n"
        "  • 使用真實帳號密碼\n"
        "  • 會自動保存 30 天\n\n"
        "**登入失敗常見原因：**\n"
        "• 帳號或密碼輸入錯誤\n"
        "• 無法連接到 HRM 系統（檢查 VPN）\n"
        "• 系統表單結構已更新（聯絡 IT）"
    )

# --- Session State 追蹤 ---
if "submit_pending" not in st.session_state:
    st.session_state.submit_pending = False

if submit_btn:
    st.session_state.submit_pending = True

# --- 執行打卡邏輯 ---
if st.session_state.submit_pending:
    if u_id and u_pw:
        expiry = datetime.now() + timedelta(days=30)
        cookie_manager.set("u_id", u_id, expires_at=expiry, key="set_uid")
        cookie_manager.set("u_pw", u_pw, expires_at=expiry, key="set_upw")
        
        with st.status("同步簽到資訊中...", expanded=True) as status:
            success, msg = run_punch(u_id, u_pw, debug=debug_mode)
            if success:
                status.update(label="✅ 簽到完成", state="complete")
                st.success(msg)
                st.balloons()
            else:
                status.update(label="❌ 簽到失敗", state="error")
                st.error(msg)
                
                # 提供額外幫助
                with st.expander("💡 故障排除建議"):
                    st.markdown(
                        "**快速檢查清單：**\n"
                        "1. 確認帳密正確\n"
                        "2. 檢查網路連接\n"
                        "3. 檢查 VPN 是否已連接\n"
                        "4. 聯絡 IT 部門：IT-Support@usuntek.com"
                    )
        
        st.session_state.submit_pending = False
    else:
        st.warning("請完整輸入資訊。")
        st.session_state.submit_pending = False