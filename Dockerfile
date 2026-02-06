# Usa uma imagem Python leve (3.10+ necessário para pydicom>=2.6.1)
FROM python:3.10-slim

# Instala dependências de sistema (build-essential para compilar libs; curl para healthcheck)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de requisitos e instala as libs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do Paics
COPY . .

# Porta padrão (Railway injeta PORT em runtime; fallback para uso local)
ENV PORT=8501
EXPOSE 8501

# Healthcheck usa a mesma porta (Railway usa isso para saber se o app está vivo)
HEALTHCHECK CMD ["sh", "-c", "curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1"]

# Comando com porta dinâmica: Railway define PORT (ex.: 8080) em runtime
# Shell form necessário para expandir $PORT
CMD ["sh", "-c", "streamlit run main.py --server.port=$PORT --server.address=0.0.0.0"]