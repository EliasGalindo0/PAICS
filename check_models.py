"""Lista modelos OpenAI disponíveis para a conta (requer OPENAI_API_KEY)."""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ ERRO: OPENAI_API_KEY não encontrada. Verifique o .env ou Railway.")
else:
    print(f"🔑 Chave carregada: {api_key[:8]}... (listando modelos com visão)\n")
    try:
        client = OpenAI(api_key=api_key)
        print("--- MODELOS (amostra; prefira modelos gpt-4o / gpt-4.1 para laudos) ---")
        found = 0
        for m in client.models.list():
            mid = getattr(m, "id", "") or ""
            if any(x in mid for x in ("gpt-4", "gpt-4o", "o1", "o3")):
                print(f"✅ {mid}")
                found += 1
                if found >= 30:
                    break
        if not found:
            print("⚠️ Nenhum modelo gpt listado (verifique permissões da chave).")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
