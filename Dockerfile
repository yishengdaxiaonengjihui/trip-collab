# 单容器同源部署：前端构建产物由 FastAPI 托管，/api 与页面同源。
# 目标运行环境：Hugging Face Spaces (Docker SDK)，监听 7860。

# --- 阶段 1：构建前端 ---
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 阶段 2：运行时 ---
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    TRIP_DB=/data/trip.db \
    SEED_DEMO=1

RUN useradd -m -u 1000 user
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/seed_demo.py frontend/seed_demo.py
COPY --from=web /web/dist frontend/dist
COPY docker/entrypoint.sh docker/entrypoint.sh

RUN chmod +x docker/entrypoint.sh && mkdir -p /data && chown -R user:user /app /data

USER user
EXPOSE 7860
CMD ["docker/entrypoint.sh"]
