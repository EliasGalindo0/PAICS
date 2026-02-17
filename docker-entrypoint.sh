#!/bin/sh
set -e

# Popular banco (admin + clínica inicial) se a conexão estiver disponível.
# Idempotente: não duplica dados se já existir.
if [ -z "$SKIP_SEED" ] || [ "$SKIP_SEED" = "0" ] || [ "$SKIP_SEED" = "false" ]; then
  echo ">>> Executando seed do banco (admin + clínica inicial)..."
  if python scripts/seed_admin.py 2>/dev/null; then
    echo ">>> Seed concluído."
  else
    echo ">>> Seed falhou ou banco indisponível; aplicação será iniciada mesmo assim."
  fi
fi

# Iniciar FastAPI em background (porta 8000)
echo ">>> Iniciando API FastAPI na porta 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Aguardar API ficar pronta
sleep 3

# Iniciar Next.js na porta exposta (Railway usa PORT)
echo ">>> Iniciando frontend Next.js na porta ${PORT:-3000}..."
cd /app/web
exec node node_modules/next/dist/bin/next start -H 0.0.0.0 -p "${PORT:-3000}"
