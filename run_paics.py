"""
Script de inicialização do PAICS
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog
import webbrowser
import time

# Configurar encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def get_base_path():
    """Obtém o caminho base da aplicação"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


def check_api_key():
    """Verifica se a API key está configurada"""
    try:
        base_path = get_base_path()
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

        # Verificar .env no diretório do executável
        if getattr(sys, 'frozen', False):
            env_path = os.path.join(os.path.dirname(sys.executable), '.env')
        else:
            env_path = os.path.join(os.path.dirname(__file__), '.env')

        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('GOOGLE_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        if key and key != '':
                            return True
        return False
    except Exception as e:
        print(f"Erro ao verificar API key: {e}")
        return False


def configure_api_key():
    """Interface para configurar API key"""
    try:
        root = tk.Tk()
        root.withdraw()

        messagebox.showinfo(
            "PAICS - Configuracao Inicial",
            "Bem-vindo ao PAICS!\n\n"
            "Para usar o sistema, voce precisa configurar sua API Key do Google Gemini.\n\n"
            "Como obter:\n"
            "1. Acesse: https://aistudio.google.com/app/apikey\n"
            "2. Faca login com sua conta Google\n"
            "3. Clique em 'Create API Key'\n"
            "4. Copie a chave gerada"
        )

        webbrowser.open("https://aistudio.google.com/app/apikey")

        api_key = simpledialog.askstring(
            "Configurar API Key",
            "Cole sua API Key do Google Gemini:",
            show='*'
        )

        if api_key:
            if getattr(sys, 'frozen', False):
                env_path = os.path.join(os.path.dirname(sys.executable), '.env')
            else:
                env_path = os.path.join(os.path.dirname(__file__), '.env')

            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f"GOOGLE_API_KEY={api_key}\n")
                f.write(f"GEMINI_MODEL_NAME=gemini-2.5-pro\n")
                f.write(f"OUTPUT_DIR=laudos_com_ia\n")

            messagebox.showinfo("Sucesso", "API Key configurada com sucesso!")
            return True
        else:
            messagebox.showwarning("Aviso", "Configuracao cancelada.")
            return False
    except Exception as e:
        print(f"Erro ao configurar API key: {e}")
        messagebox.showerror("Erro", f"Erro: {str(e)}")
        return False


def create_streamlit_config():
    """Cria arquivo de configuração do Streamlit para evitar conflitos"""
    try:
        if getattr(sys, 'frozen', False):
            config_dir = os.path.join(os.path.dirname(sys.executable), '.streamlit')
        else:
            config_dir = os.path.join(os.path.dirname(__file__), '.streamlit')

        os.makedirs(config_dir, exist_ok=True)

        config_file = os.path.join(config_dir, 'config.toml')

        config_content = """[global]
developmentMode = false

[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = 8501

[logger]
level = "error"
"""

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)

        print(f"Config criado: {config_file}")
        return config_dir

    except Exception as e:
        print(f"Aviso: nao foi possivel criar config: {e}")
        return None


def launch_streamlit():
    """Lança o Streamlit"""
    try:
        base_path = get_base_path()
        streamlit_script = os.path.join(base_path, 'streamlit_app.py')

        print(f"Base: {base_path}")
        print(f"Script: {streamlit_script}")

        if not os.path.exists(streamlit_script):
            raise FileNotFoundError(f"Arquivo nao encontrado: {streamlit_script}")

        # Criar configuração do Streamlit
        config_dir = create_streamlit_config()

        # Configurar variáveis de ambiente
        env = os.environ.copy()
        env['PYTHONPATH'] = base_path

        # Desabilitar modo de desenvolvimento
        env['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'

        if config_dir:
            env['STREAMLIT_CONFIG_DIR'] = config_dir

        # Carregar .env
        if getattr(sys, 'frozen', False):
            env_file = os.path.join(os.path.dirname(sys.executable), '.env')
        else:
            env_file = os.path.join(os.path.dirname(__file__), '.env')

        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env[key] = value

        print("Iniciando Streamlit...")

        # Usar API interna do streamlit
        import streamlit.web.cli as stcli

        # Configurar sys.argv para streamlit (SEM --server.port para evitar conflito)
        sys.argv = [
            "streamlit",
            "run",
            streamlit_script,
        ]

        # Thread para abrir navegador
        def open_browser():
            time.sleep(3)
            print("Abrindo navegador...")
            webbrowser.open('http://localhost:8501')

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

        print("Aplicacao iniciada! Feche esta janela para encerrar.")

        # Executar streamlit
        sys.exit(stcli.main())

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Erro", f"Erro ao iniciar:\n\n{str(e)}")
        input("Pressione ENTER para fechar...")


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("PAICS - Sistema de Analise de Imagens Veterinarias")
        print("=" * 60)
        print()

        print("Verificando configuracao...")
        if not check_api_key():
            print("Configuracao necessaria...")
            if not configure_api_key():
                print("Configuracao cancelada.")
                input("Pressione ENTER para fechar...")
                sys.exit(1)

        print("Configuracao OK!")
        print()
        print("Lancando aplicacao...")
        launch_streamlit()

    except Exception as e:
        print("=" * 60)
        print("ERRO FATAL")
        print("=" * 60)
        print(f"\n{e}\n")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        input("\nPressione ENTER para fechar...")
        sys.exit(1)
