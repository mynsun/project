import streamlit as st
import pymysql
import streamlit.components.v1 as components

# DB 연결 정보
DB_HOST = '13.124.198.232'
DB_USER = 'root'
DB_PASSWORD = '1234'
DB_NAME = 'users'

def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8'
    )

def signup(userid, username, password):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (userid, username, password) VALUES (%s, %s, %s)",
            (userid, username, password)
        )
        conn.commit()
        return True
    except pymysql.err.IntegrityError:
        return False
    finally:
        conn.close()

def login(userid, password):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT password, username FROM users WHERE userid=%s", (userid,))
    row = cursor.fetchone()
    conn.close()
    if row:
        if password == row[0]:
            return True, row[1]
    return False, None

# 세션 상태 초기화
if 'show_signup' not in st.session_state:
    st.session_state['show_signup'] = False
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

# 로그인 성공 시 자동으로 메인 페이지(index.html)로 리다이렉트
if st.session_state['logged_in']:
    # 부모 창(HTML)에 메시지 전송
    js_code = f"""
    <script>
    window.parent.postMessage(
        {{
            "type": "loginSuccess",
            "username": "{st.session_state['username']}"
        }},
        "*"
    );
    </script>
    """
    components.html(js_code, height=0, width=0)
    
    # 리다이렉트 메시지 표시
    st.success(f"{st.session_state['username']}님, 환영합니다! 메인 페이지로 이동합니다.")
    st.markdown('<meta http-equiv="refresh" content="2;url=index.html">', unsafe_allow_html=True)
    
else:

    def show_signup_form():
        st.subheader("회원가입")
        with st.form("signup_form"):
            userid = st.text_input("아이디", key="signup_userid")
            username = st.text_input("이름", key="signup_username")
            password = st.text_input("비밀번호", type="password", key="signup_pw")
            submit_button = st.form_submit_button("가입하기")
            if submit_button:
                if not userid or not username or not password:
                    st.error("모든 필드를 입력해주세요.")
                elif signup(userid, username, password):
                    st.success("회원가입 성공! 로그인해주세요.")
                    st.session_state['show_signup'] = False
                else:
                    st.error("이미 사용 중인 아이디입니다.")

    def show_login_form():
        st.subheader("로그인")
        userid = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if not userid or not password:
                st.error("아이디와 비밀번호를 입력해주세요.")
            else:
                success, username = login(userid, password)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
        st.markdown("---")
        if st.button("회원가입"):
            st.session_state['show_signup'] = True

    if st.session_state['show_signup']:
        show_signup_form()
        if st.button("← 로그인 화면으로 돌아가기"):
            st.session_state['show_signup'] = False
    else:
        show_login_form()
