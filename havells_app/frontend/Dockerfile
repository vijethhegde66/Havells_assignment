FROM python:3.11-slim

WORKDIR /app

COPY frontend/requirements.txt /app/frontend/
RUN pip install --no-cache-dir -r frontend/requirements.txt

COPY frontend/ /app/frontend/

WORKDIR /app/frontend

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
