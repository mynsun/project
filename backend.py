from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymysql

app = FastAPI()

# MySQL 연결 설정
def get_db_connection():
    return pymysql.connect(
        host="13.124.198.232",
        user="root",
        password="1234",
        database="users",
        charset="utf8"
    )

# 데이터 모델
class SignupRequest(BaseModel):
    userid: str
    username: str
    password: str

class LoginRequest(BaseModel):
    userid: str
    password: str

# 회원가입 엔드포인트
@app.post("/signup")
def signup(req: SignupRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 아이디 중복 확인
        cursor.execute("SELECT * FROM users WHERE userid = %s", (req.userid,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
        # 사용자 추가
        cursor.execute(
            "INSERT INTO users (userid, username, password) VALUES (%s, %s, %s)",
            (req.userid, req.username, req.password)
        )
        conn.commit()
        return {"message": "회원가입 성공"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# 로그인 엔드포인트
@app.post("/login")
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT username, password FROM users WHERE userid = %s",
            (req.userid,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")
        username, db_password = row
        if req.password != db_password:
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")
        # 로그인 성공 시 사용자 이름 반환
        return {"username": username}
    finally:
        cursor.close()
        conn.close()
