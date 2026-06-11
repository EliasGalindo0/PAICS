"""Testa carregamento do .env e OPENAI_API_KEY."""
import os

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY", "NÃO_ENCONTRADA")
model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

print(f"OPENAI_MODEL_NAME={model}")

if api_key == "NÃO_ENCONTRADA" or not api_key.strip():
    print("❌ Variável OPENAI_API_KEY não encontrada!")
    print("")
    print("Configure:")
    print("  1. Copie .env.example para .env")
    print("  2. Defina OPENAI_API_KEY=sua_chave")
    raise SystemExit(1)

if api_key in ("sua_chave_aqui", "SUA_API_KEY_AQUI"):
    print("⚠️  OPENAI_API_KEY encontrada, mas com valor padrão!")
    raise SystemExit(1)

print("✅ Variável OPENAI_API_KEY carregada com sucesso!")
