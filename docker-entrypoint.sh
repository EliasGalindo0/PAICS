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

# Iniciar a aplicação (substitui o shell pelo streamlit)
exec streamlit run streamlit_app.py --server.port="${PORT:-8501}" --server.address=0.0.0.0
