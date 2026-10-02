FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

ARG PIP_INDEX_URL=https://pypi.org/simple
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements.txt

COPY app ./app
RUN python -m compileall -q app

EXPOSE 8087
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8087"]
