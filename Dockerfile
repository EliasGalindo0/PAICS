# Stage 1: Build Next.js
FROM node:20-alpine AS web-builder
WORKDIR /app/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# Stage 2: Produção (Python + Node)
FROM python:3.12

# Node.js via Debian (evita NodeSource que pode falhar no Railway)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código do projeto (web será sobrescrito pelo build)
COPY . .

# Next.js: sobrescrever com build de produção
COPY --from=web-builder /app/web ./web

ENV PORT=3000
ENV NODE_ENV=production
EXPOSE 3000

RUN chmod +x docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/ || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
