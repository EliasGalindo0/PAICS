# Stage 1: Build Next.js
FROM node:20-alpine AS web-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci 2>/dev/null || npm install
COPY web/ ./
RUN npm run build

# Stage 2: Produção (Python + Node para next start)
FROM python:3.12-slim

# build-essential para deps Python; curl para healthcheck; Node.js para Next.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código da API e assets
COPY logo/ logo/
COPY api/ api/
COPY auth/ auth/
COPY database/ database/
COPY scripts/ scripts/
COPY utils/ utils/
COPY main.py .
COPY docker-entrypoint.sh .

# Next.js: copiar build e node_modules do stage anterior
COPY --from=web-builder /app/web/.next ./web/.next
COPY --from=web-builder /app/web/node_modules ./web/node_modules
COPY --from=web-builder /app/web/package.json ./web/package.json
COPY web/public ./web/public

# Railway usa PORT em runtime; Next.js como processo principal
ENV PORT=3000
EXPOSE 3000

RUN chmod +x docker-entrypoint.sh

# Healthcheck: Next.js na raiz
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
