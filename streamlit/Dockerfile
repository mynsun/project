FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

ENV STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# # Step 1 :
# FROM node:20.19.1

# # Step 2:
# WORKDIR /app
# #/usr/src/app

# # Step 3:
# COPY package*.json .
# RUN npm install

# RUN npm install -g pm2

# COPY . .

# # Step 5:
# EXPOSE 3000

# # Step 6:
# CMD ["pm2-runtime", "app.js"]