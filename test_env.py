#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para verificar se o arquivo .env está sendo carregado corretamente.
"""

from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Verificar se a variável está sendo carregada
api_key = os.getenv("GOOGLE_API_KEY", "NÃO_ENCONTRADA")

print("=" * 60)
print("Teste de Carregamento de Variáveis de Ambiente (.env)")
print("=" * 60)
print()

if api_key == "NÃO_ENCONTRADA":
    print("❌ Variável GOOGLE_API_KEY não encontrada!")
    print()
    print("Certifique-se de que:")
    print("  1. O arquivo .env existe na raiz do projeto")
    print("  2. O arquivo .env contém: GOOGLE_API_KEY=sua_chave_aqui")
    print("  3. Você copiou o arquivo .env.example para .env")
    print()
elif api_key == "SUA_API_KEY_AQUI" or api_key == "":
    print("⚠️  Variável GOOGLE_API_KEY encontrada, mas com valor padrão!")
    print()
    print("Edite o arquivo .env e adicione sua chave real da API.")
else:
    # Mostrar apenas os primeiros e últimos caracteres da chave por segurança
    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
    print("✅ Variável GOOGLE_API_KEY carregada com sucesso!")
    print(f"   Chave (mascarada): {masked}")
    print(f"   Tamanho: {len(api_key)} caracteres")

print()
print("=" * 60)
