FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_MODE=true \
    HOSTED_DEMO=true

WORKDIR /home/user/app
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 1000 user

# Explicit copies prevent local credentials, SQLite state and model weights entering the image.
COPY --chown=user:user app ./app
COPY --chown=user:user data/graph.json data/anchors.json data/roads.geojson ./data/
USER user

EXPOSE 7860
CMD ["uvicorn", "app.hosted:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--ws", "websockets", "--ws-ping-interval", "30", "--ws-ping-timeout", "120"]
