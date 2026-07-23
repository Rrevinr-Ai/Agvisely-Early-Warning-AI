# Backend — FastAPI
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY *.xlsx ./

ENV PYTHONUNBUFFERED=1
EXPOSE 9603

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9603"]
