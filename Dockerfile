# Imagem completa (não slim): OpenSSL do Debian full costuma resolver TLSV1_ALERT_INTERNAL_ERROR com Atlas no Railway
FROM python:3.12

# build-essential para compilar deps; curl para healthcheck (ca-certificates já na imagem full)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de requisitos e instala as libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do Paics
COPY . .

# Entrypoint: seed do banco (admin + clínica) e depois inicia o Streamlit
RUN chmod +x docker-entrypoint.sh

# Porta padrão (Railway injeta PORT em runtime; fallback para uso local)
ENV PORT=8501
EXPOSE 8501

# Healthcheck usa a mesma porta (Railway usa isso para saber se o app está vivo)
HEALTHCHECK CMD ["sh", "-c", "curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1"]

# Seed do banco na subida; para pular: SKIP_SEED=1
ENTRYPOINT ["./docker-entrypoint.sh"]