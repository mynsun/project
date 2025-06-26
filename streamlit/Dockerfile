FROM python:3.9-slim-buster

WORKDIR /app

COPY ../streamlit .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

ENV STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
