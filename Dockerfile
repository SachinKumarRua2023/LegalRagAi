FROM python:3.11.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p chroma_db data/raw data/processed data/uploads

ENV PORT=8000
CMD uvicorn backend.api:app --host 0.0.0.0 --port ${PORT}
