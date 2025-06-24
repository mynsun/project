import streamlit as st
import pymysql
import bcrypt

# MySQL 연결
conn = pymysql.connect(
    host='13.124.198.232',   # 예: '13.124.198.232'
    user='root',   # 생성한 MySQL 사용자
    password='1234', # 설정한 비밀번호
    db='users', # 예: 'testdb'
    charset='utf8'
)
cursor = conn.cursor()

# 회원가입 함수
def signup(username, password):
    # 비밀번호 해시
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
        conn.commit()
        return True
    except pymysql.err.IntegrityError:
        return False

# 로그인 함수
def login(username, password):
    cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
    row = cursor.fetchone()
    if row and bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
        return True
    return False

# Streamlit UI
st.title("회원가입 / 로그인")

menu = st.sidebar.selectbox("메뉴 선택", ["로그인", "회원가입"])

if menu == "회원가입":
    st.subheader("회원가입")
    new_user = st.text_input("사용자 이름")
    new_password = st.text_input("비밀번호", type="password")
    if st.button("회원가입"):
        if signup(new_user, new_password):
            st.success("회원가입 성공! 로그인 해주세요.")
        else:
            st.error("이미 존재하는 사용자입니다.")

elif menu == "로그인":
    st.subheader("로그인")
    username = st.text_input("사용자 이름")
    password = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if login(username, password):
            st.success(f"{username}님, 환영합니다!")
        else:
            st.error("아이디 또는 비밀번호가 틀렸습니다.")

conn.close()
