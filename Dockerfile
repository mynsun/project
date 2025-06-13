FROM python:3.9-slim

# 작업 디렉토리 설정
ENV APP_PATH /opt/streamlit_app
WORKDIR $APP_PATH

# 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY streamlit_app.py .

# 필요시 추가 폴더 복사
# COPY static/ $APP_PATH/static/
# COPY templates/ $APP_PATH/templates/

# Streamlit 환경설정
ENV STREAMLIT_SERVER_HEADLESS=true

# 포트 노출
EXPOSE 8501

# 앱 실행
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]