FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --system --uid 10001 --create-home bot

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

COPY --chown=bot:bot . /app/
RUN mkdir -p /app/data && chown -R bot:bot /app

USER bot

CMD ["python", "main.py"]
