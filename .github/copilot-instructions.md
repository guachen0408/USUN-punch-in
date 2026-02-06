# AI Coding Agent Instructions - USUN Punch-in System

## Project Overview
USUN-punch-in is a Streamlit-based web automation tool that automates employee check-in (punch-in) to a company HRM system. It uses session-based HTTP requests with HTML parsing to simulate browser login and form submission workflows.

## Architecture & Data Flow

### Core Components
1. **Streamlit UI Layer** ([app.py](../app.py)): Provides text inputs for employee ID/password and a submit button; uses `extra_streamlit_components.CookieManager` to persist credentials locally for 30 days
2. **Request Session Management**: Uses `requests.Session()` to maintain authentication state across multiple requests
3. **HTML Parser**: BeautifulSoup extracts ViewState and other form fields from ASP.NET responses
4. **Authentication Flow**: 
   - GET `/Ez-Portal/Login.aspx` → extract form fields & ViewState
   - POST login credentials with extracted fields → server validates
   - Redirect indicates successful login
5. **Punch-in Submission**:
   - GET `/Ez-Portal/Employee/PunchOutBaiDu.aspx` → extract updated ViewState
   - POST Ajax request with special headers (`X-MicrosoftAjax: Delta=true`, `X-Requested-With: XMLHttpRequest`) to bypass anti-bot checks
   - Response contains "簽到完成" (punch success) or error message

## Critical Patterns & Conventions

### ASP.NET Form Handling
- Always extract **all** `<input>` tags with their `name` and `value` attributes using: `{tag.get('name'): tag.get('value', '') for tag in soup.find_all('input') if tag.get('name')}`
- ViewState fields are essential and must be preserved across requests—parse them fresh from each page to avoid staleness
- Special fields like `__EVENTTARGET`, `__EVENTARGUMENT`, `__ASYNCPOST` control form submission type; must match server expectations

### Browser Simulation
- User-Agent header must be a modern Chrome/Webkit string—server rejects outdated agents
- Include `Accept-Language: zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7` for proper localization
- Ajax requests require `X-MicrosoftAjax: Delta=true` and `X-Requested-With: XMLHttpRequest` headers—omitting these causes form rejection
- Set `Content-Type: application/x-www-form-urlencoded; charset=UTF-8` for POST payloads

### Error Handling
- Check for success keyword "簽到完成" in response text—presence confirms successful punch
- Extract Chinese error messages from response using `re.findall(r'[\u4e00-\u9fa5]+', response.text)` to provide user feedback
- Distinguish between authentication failure (`"Login.aspx" in response.url and "ReturnUrl" not in response.url`) and punch-in failure via response content inspection
- Never assume silent failures; always parse response content for error indicators

### Credential Persistence
- Cookies are set in Streamlit UI via `cookie_manager.set()` with 30-day expiry
- Cookies are retrieved on page load via `cookie_manager.get_all()` to pre-fill input fields
- Key names: `"u_id"` for employee ID, `"u_pw"` for password

## Dependencies
- [requests](https://docs.python-requests.org): HTTP session management and form submission
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/): HTML parsing and form field extraction
- [streamlit](https://streamlit.io/): UI framework (`st.title`, `st.text_input`, `st.button`)
- [extra-streamlit-components](https://github.com/Mohamed-512/Extra-Streamlit-Components): Cookie manager for credential persistence

## Development & Testing
- Run app: `streamlit run app.py`
- No test suite exists; test punch-in flows manually against staging/production HRM system
- Credential security: Consider environment variable support (e.g., `os.environ.get("USUN_ID")`) for deployment to avoid hardcoding
- Session timeout: Server may invalidate sessions after period of inactivity—retry logic recommended for production use

## Common Tasks & Patterns

**Modifying Input Fields**: Update field names in `payload_l` and `payload_p` dicts; always cross-check with actual form HTML returned by server (field names may change with HRM updates)

**Adding New Punch Types**: Create separate POST endpoints similar to `PunchOutBaiDu.aspx`; reuse session management and ViewState extraction logic to stay DRY

**Debugging Forms**: Print `soup.find_all('input')` output and `response.text` to verify server response structure; ASP.NET form changes frequently and require manual inspection

## External URL
- HRM System Base URL: `https://usun-hrm.usuntek.com` (production)
- Login endpoint: `/Ez-Portal/Login.aspx`
- Punch-in endpoint: `/Ez-Portal/Employee/PunchOutBaiDu.aspx`
