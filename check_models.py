import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega seu .env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ ERRO: Chave não encontrada. Verifique o .env")
else:
    genai.configure(api_key=api_key)
    print(f"🔑 Chave carregada: {api_key[:5]}... (verificando modelos disponíveis...)\n")

    try:
        print("--- MODELOS DISPONÍVEIS PARA SUA CONTA ---")
        found = False
        for m in genai.list_models():
            # Filtra apenas modelos que geram texto/conteúdo
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ {m.name}")
                found = True

        if not found:
            print("⚠️ Nenhum modelo de geração de conteúdo encontrado. Sua chave pode estar restrita ou sem cota.")

    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
