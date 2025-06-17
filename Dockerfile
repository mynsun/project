# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 시스템 종속성 설치 (필요시)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# Streamlit 설정
EXPOSE 8501
ENV STREAMLIT_SERVER_HEADLESS=true
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
