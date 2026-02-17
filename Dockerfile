# Stage 1: Build Next.js
FROM node:20-alpine AS web-builder
WORKDIR /app/web
ENV NODE_OPTIONS=--max-old-space-size=4096
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Base Node (evita NodeSource) + Python para API
FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf python3 /usr/bin/python && ln -sf pip3 /usr/bin/pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Next.js build completo (para next start)
COPY --from=web-builder /app/web ./web

ENV PORT=3000
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
EXPOSE 3000

RUN chmod +x docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
