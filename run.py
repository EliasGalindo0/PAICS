#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script auxiliar para executar o PAICS de forma mais interativa.
Permite escolher o arquivo PDF a ser processado.
"""

import os
import sys
from pathlib import Path

# Importar as classes do main
try:
    from main import VetReportGenerator, API_KEY
except ImportError:
    print("❌ Erro: Não foi possível importar o módulo main.py")
    print(
        "Certifique-se de que todos os arquivos necessários estão "
        "presentes."
    )
    sys.exit(1)


def main():
    """Função principal do script auxiliar."""
    print("=" * 60)
    print("PAICS - Sistema de Análise de Imagens Veterinárias")
    print("=" * 60)
    print()

    # Verificar API Key
    if "SUA_API_KEY_AQUI" in API_KEY or not API_KEY:
        print("⚠️  AVISO: API Key não configurada!")
        print("Configure a variável de ambiente GOOGLE_API_KEY ou edite main.py")
        print()
        response = input(
            "Deseja continuar mesmo assim? (s/N): ").strip().lower()
        if response != 's':
            print("Operação cancelada.")
            sys.exit(0)

    # Solicitar arquivo PDF
    print("Arquivos PDF na pasta atual:")
    pdf_files = list(Path('.').glob('*.pdf'))
    if pdf_files:
        print()
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"  {i}. {pdf_file.name}")
        print()
    else:
        print("  (nenhum arquivo PDF encontrado)")
        print()

    pdf_path = input("Digite o caminho do arquivo PDF: ").strip()

    # Remover aspas se o usuário colocou
    pdf_path = pdf_path.strip('"').strip("'")

    if not pdf_path:
        print("❌ Caminho não informado. Operação cancelada.")
        sys.exit(1)

    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    # Processar
    print()
    print("Iniciando processamento...")
    print()

    try:
        generator = VetReportGenerator()
        generator.create_report(pdf_path)
        print()
        print("✅ Processamento concluído com sucesso!")
    except Exception as e:
        print()
        print(f"❌ Erro durante o processamento: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
