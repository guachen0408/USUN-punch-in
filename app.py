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

# --- 模式選擇 ---
st.sidebar.title("⚙️ 設定")
mode = st.sidebar.radio(
    "選擇模式",
    options=["🚀 正常模式 (生產)", "🧪 測試模式 (模擬)", "🔧 診斷工具"],
    help="正常模式連接真實系統，測試模式用於開發測試"
)


# ============ 診斷模式 ============
if mode == "🔧 診斷工具":
    st.title("🔧 網路診斷工具")
    st.markdown("---")
    
    st.info(
        "**如何使用此工具：**\n\n"
        "1️⃣ 若網路連接正常 → 點擊測試按鈕  \n"
        "2️⃣ 若無法連接 → 按照下方建議排查  \n"
        "3️⃣ 若仍無法解決 → 請聯絡 IT 部門  \n\n"
        "**⚙️ 切換至 🧪 測試模式 可跳過網路依賴，直接測試應用功能**"
    )
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📡 連線測試")
        timeout_val = st.slider("逾時設定 (秒)", min_value=3, max_value=30, value=10)
        
        if st.button("🔄 測試 HRM 系統連線", use_container_width=True):
            with st.spinner(f"測試中 (超時:{timeout_val}秒)..."):
                try:
                    response = requests.get(
                        "https://usun-hrm.usuntek.com/Ez-Portal/Login.aspx", 
                        timeout=timeout_val,
                        verify=False
                    )
                    st.success(f"✅ 連線成功！\n\n狀態碼：{response.status_code}\n回應時間：{response.elapsed.total_seconds():.2f}秒")
                    st.info(f"📊 伺服器類型：{response.headers.get('Server', '未知')}")
                    
                except requests.exceptions.Timeout:
                    st.error(
                        f"⏱️ **連線逾時** ({timeout_val}秒無回應)\n\n"
                        "**可能原因：**\n"
                        "• 🔌 網路不通或伺服器離線\n"
                        "• 🧱 防火牆限制連接\n"
                        "• 🌐 DNS 解析緩慢\n\n"
                        "**建議方案：**\n"
                        "1. 檢查網路連接\n"
                        "2. 確認 VPN 已連接\n"
                        "3. 嘗試增加逾時秒數再試一次\n"
                        "4. 聯絡 IT 部門確認系統狀態"
                    )
                    
                except requests.exceptions.ConnectionError:
                    st.error(
                        "🔌 **連線失敗** (無法建立連接)\n\n"
                        "**可能原因：**\n"
                        "• 網路完全不通\n"
                        "• DNS 查詢失敗\n"
                        "• 防火牆阻止\n\n"
                        "**建議方案：**\n"
                        "1. 檢查網路連接\n"
                        "2. 驗證 VPN 狀態\n"
                        "3. 測試其他網址"
                    )
                    
                except requests.exceptions.SSLError:
                    st.error(
                        "🔐 **SSL/TLS 驗證失敗**\n\n"
                        "伺服器憑證可能過期或不受信任"
                    )
                    
                except Exception as e:
                    st.error(f"❌ 未知錯誤：{str(e)}")
    
    with col2:
        st.subheader("🌐 DNS 查詢")
        
        if st.button("🔍 解析 usun-hrm.usuntek.com", use_container_width=True):
            try:
                ip = socket.gethostbyname("usun-hrm.usuntek.com")
                st.success(f"✅ DNS 解析成功\n\n域名：usun-hrm.usuntek.com\nIP 地址：{ip}")
                
                # 嘗試 ping IP
                result = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result.settimeout(3)
                ping_result = result.connect_ex((ip, 443))
                result.close()
                
                if ping_result == 0:
                    st.success("✅ HTTPS 連接埠 (443) 可達")
                else:
                    st.warning("⚠️ HTTPS 連接埠 (443) 無法訪問，可能被防火牆阻止")
                    
            except socket.gaierror:
                st.error(
                    "❌ **DNS 查詢失敗** (無法解析域名)\n\n"
                    "**可能原因：**\n"
                    "• DNS 伺服器無法訪問\n"
                    "• 域名不存在\n"
                    "• 網路不通\n\n"
                    "**建議方案：**\n"
                    "1. 確認網路連接\n"
                    "2. 檢查 DNS 設定\n"
                    "3. 聯絡 IT 部門"
                )
            except Exception as e:
                st.error(f"❌ 錯誤：{str(e)}")
    
    st.markdown("---")
    st.subheader("� HRM 登入頁面檢查")
    
    if st.button("📄 獲取登入頁面內容", use_container_width=True):
        with st.spinner("正在獲取登入頁面..."):
            try:
                response = requests.get(
                    "https://usun-hrm.usuntek.com/Ez-Portal/Login.aspx",
                    timeout=10,
                    verify=False
                )
                
                st.success(f"✅ 頁面獲取成功")
                st.write(f"**狀態碼：** {response.status_code}")
                st.write(f"**內容類型：** {response.headers.get('Content-Type', '未知')}")
                st.write(f"**頁面大小：** {len(response.text)} 字元")
                
                # 解析表單
                soup = BeautifulSoup(response.text, 'html.parser')
                input_fields = soup.find_all('input')
                
                if input_fields:
                    st.write(f"**✅ 找到 {len(input_fields)} 個表單欄位：**")
                    
                    # 顯示所有表單字段
                    field_data = {}
                    for inp in input_fields:
                        name = inp.get('name')
                        value = inp.get('value', '')[:50]  # 只顯示前 50 字
                        field_type = inp.get('type', 'text')
                        if name:
                            field_data[name] = f"類型: {field_type}, 值: {value if value else '(空)'}"
                    
                    with st.expander("📋 所有表單欄位詳情"):
                        for name, info in field_data.items():
                            st.code(f"{name}\n  {info}")
                    
                    # 找出可能的登入字段
                    st.write("**🔎 可能的登入欄位：**")
                    login_fields = []
                    for name in field_data.keys():
                        if any(keyword in name.lower() for keyword in ['login', 'user', 'account', 'id', 'work', 'emp']):
                            login_fields.append(name)
                    
                    if login_fields:
                        for field in login_fields:
                            st.code(f"✓ {field}")
                    else:
                        st.warning("⚠️ 無法自動識別登入欄位，請查看完整列表")
                else:
                    st.warning("⚠️ 未找到表單欄位，頁面結構可能已更新")
                
                # 顯示完整 HTML（可折疊）
                with st.expander("📜 完整頁面 HTML（前 2000 字）"):
                    st.code(response.text[:2000], language="html")
                    
            except requests.exceptions.Timeout:
                st.error("⏱️ 連線逾時 - 無法在 10 秒內獲得回應")
            except requests.exceptions.ConnectionError:
                st.error("🔌 連線失敗 - 網路不通或伺服器離線")
            except Exception as e:
                st.error(f"❌ 錯誤：{str(e)}")
    
    st.markdown("---")
    
    with st.expander("❓ 不同錯誤類型的含義"):
        st.markdown(
            "**✅ 連線成功**\n"
            "→ 系統正常運行，可使用正常模式\n\n"
            "**⏱️ 連線逾時**\n"
            "→ 伺服器無回應，可能網路延遲高或伺服器離線\n\n"
            "**🔌 連線失敗**\n"
            "→ TCP 連接被拒絕，通常是防火牆限制\n\n"
            "**❌ DNS 失敗**\n"
            "→ 無法解析域名，DNS 配置問題\n\n"
            "**🔐 SSL 驗證失敗**\n"
            "→ 伺服器憑證問題，通常需要聯絡 IT"
        )
    
    with st.expander("💡 故障排除步驟"):
        st.markdown(
            "**第 1 步：確認網路**\n"
            "```\n"
            "ping 8.8.8.8  # Google DNS\n"
            "```\n\n"
            "**第 2 步：檢查 VPN**\n"
            "確認 VPN 客戶端已連接\n\n"
            "**第 3 步：嘗試其他 DNS**\n"
            "```\n"
            "nslookup usun-hrm.usuntek.com 8.8.8.8\n"
            "```\n\n"
            "**第 4 步：聯絡 IT**\n"
            "若以上步驟都失敗，請聯絡 IT 部門提供上述診斷結果"
        )
    
    st.success(
        "**💡 開發環境中的替代方案：**\n\n"
        "👉 切換至 🧪 **測試模式** 可以完整測試應用功能，無需網路連接！"
    )
    st.stop()

# ============ 測試模式 ============
if mode == "🧪 測試模式 (模擬)":
    st.title("🧪 測試模式")
    st.markdown("---")
    st.info("ℹ️ 此模式模擬打卡流程，用於開發測試，不連接真實系統")
    
    st.subheader("🔐 員工登入")
    u_id = st.text_input("工號", value=saved_id or "E12345", placeholder="請輸入工號", key="test_id_input")
    u_pw = st.text_input("密碼", type="password", value=saved_pw or "test", placeholder="請輸入密碼", key="test_pw_input")
    
    if st.button("🚀 模擬打卡", use_container_width=True, type="primary"):
        if u_id and u_pw:
            expiry = datetime.now() + timedelta(days=30)
            cookie_manager.set("u_id", u_id, expires_at=expiry, key="test_set_uid")
            cookie_manager.set("u_pw", u_pw, expires_at=expiry, key="test_set_upw")
            
            with st.status("模擬簽到資訊中...", expanded=True) as status:
                # 步驟 1
                st.write("📡 步驟 1/3 - 連線到登入頁面...")
                progress = st.progress(0)
                for i in range(100):
                    progress.progress(i + 1)
                    time.sleep(0.01)
                st.write("✅ 連線成功（回應時間：0.68秒）")
                
                # 步驟 2
                st.write("📡 步驟 2/3 - 提交登入認證...")
                progress = st.progress(0)
                for i in range(100):
                    progress.progress(i + 1)
                    time.sleep(0.015)
                st.write(f"✅ 身份認證成功（處理時間：1.5秒）")
                st.write(f"   • 用戶工號：{u_id}")
                
                # 步驟 3
                st.write("📡 步驟 3/3 - 發送打卡請求...")
                progress = st.progress(0)
                for i in range(100):
                    progress.progress(i + 1)
                    time.sleep(0.008)
                st.write("✅ 伺服器已收到打卡請求，正在處理...")
                
                # 暫停並顯示成功
                time.sleep(0.5)
                status.update(label="✅ 模擬打卡完成", state="complete")
                
                st.success("🎉 模擬簽到完成！\n\n沽號：" + u_id + "\n時間：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                st.balloons()
        else:
            st.warning("請完整輸入資訊。")
    st.stop()

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
            "1️⃣ **無法連接** → 使用侧边栏 🔧 診斷工具\n"
            "2️⃣ **想測試** → 切換至 🧪 測試模式\n"
            "3️⃣ **需更多信息** → 展開下方「使用說明」"
        )

with st.expander("📖 使用說明"):
    st.markdown(
        "**功能介紹：**\n\n"
        "🚀 **正常模式** - 連接真實 HRM 系統\n"
        "  • 需要網路連接正常\n"
        "  • 使用真實帳號密碼\n"
        "  • 會自動保存 30 天\n\n"
        "🧪 **測試模式** - 開發測試用\n"
        "  • 不需網路連接\n"
        "  • 完整模擬打卡流程\n"
        "  • 適合功能驗證\n\n"
        "🔧 **診斷工具** - 網路故障排查\n"
        "  • 測試連線狀態\n"
        "  • DNS 查詢測試\n"
        "  • 詳細故障排除指南\n\n"
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
                        "2. 使用 🔧 診斷工具 測試網路\n"
                        "3. 檢查 VPN 是否已連接\n"
                        "4. 若網路正常無法登入，嘗試 🧪 測試模式\n"
                        "5. 聯絡 IT 部門：IT-Support@usuntek.com"
                    )
        
        st.session_state.submit_pending = False
    else:
        st.warning("請完整輸入資訊。")
        st.session_state.submit_pending = False