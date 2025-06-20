FROM python:3.11-slim

WORKDIR /app

ARG CACHEBUST=0

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt


COPY . .

CMD uvicorn main:app --host 0.0.0.0 --port $PORT