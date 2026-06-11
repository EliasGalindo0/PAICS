"""
Configurações centralizadas do PAICS
"""
import os
from dotenv import load_dotenv
import sys

# Carregar .env do diretório correto
if getattr(sys, 'frozen', False):
    # Executável: .env está ao lado do .exe
    env_path = os.path.join(os.path.dirname(sys.executable), '.env')
else:
    # Script: .env está no diretório do script
    env_path = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)

# API Configuration (OpenAI — laudos com visão)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
OPENAI_FALLBACK_MODEL_NAME = os.getenv("OPENAI_FALLBACK_MODEL_NAME", "")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180"))

# Directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "laudos_com_ia")
STREAMLIT_TEMP_DIR = os.getenv("STREAMLIT_TEMP_DIR", "temp_laudos")

# Pasta de uploads (imagens das requisições).
# Em produção com Railway: use um Volume montado em /data e defina UPLOADS_DIR=/data/uploads
# para que os uploads persistam entre deploys.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.getenv("UPLOADS_DIR") or os.path.join(_PROJECT_ROOT, "uploads")

# Logo (asset estático; em Docker/Railway fica em /app/logo/)
LOGO_PATH = os.path.join(_PROJECT_ROOT, "logo", "PAICS.jpeg")

# PDF Processing
PDF_ZOOM_FACTOR = float(os.getenv("PDF_ZOOM_FACTOR", "2.0"))

# Document Settings
IMAGE_WIDTH_INCHES = float(os.getenv("IMAGE_WIDTH_INCHES", "5.5"))
DOC_FONT_NAME = os.getenv("DOC_FONT_NAME", "Calibri")
DOC_FONT_SIZE = int(os.getenv("DOC_FONT_SIZE", "11"))

# OCR Settings
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "por+eng")

# App Metadata
APP_NAME = "PAICS"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Sistema de Análise de Imagens Veterinárias"
