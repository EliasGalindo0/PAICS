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

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")

# Directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "laudos_com_ia")
STREAMLIT_TEMP_DIR = os.getenv("STREAMLIT_TEMP_DIR", "temp_laudos")

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
