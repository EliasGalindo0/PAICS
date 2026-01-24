"""
Analisador de imagens veterinárias com Gemini (LLM).
Usado pelo user_dashboard, admin_dashboard e main sem depender de PyMuPDF/docx.
"""
from __future__ import annotations

import os
import re
import sys
from typing import List, Optional

import warnings

from dotenv import load_dotenv
from PIL import Image

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
API_KEY = os.getenv("GOOGLE_API_KEY", "SUA_API_KEY_AQUI")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
genai.configure(api_key=API_KEY)


def _safe_print(*args, **kwargs) -> None:
    """Print que não quebra em consoles Windows com encoding legado."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        text = sep.join(str(a) for a in args) + end
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        try:
            sys.stdout.write(
                text.encode(encoding, errors="replace").decode(
                    encoding, errors="replace"
                )
            )
        except Exception:
            buf = text.encode("utf-8", errors="replace").decode(
                "utf-8", errors="replace"
            )
            sys.stdout.write(buf)


def load_dicom_image(dicom_path: str) -> Optional[Image.Image]:
    """Converte arquivo DICOM em imagem PIL."""
    try:
        import numpy as np  # pydicom exige NumPy para pixel_array -> ndarray
        import pydicom
        from pydicom.pixel_data_handlers.util import apply_voi_lut

        dcm = pydicom.dcmread(dicom_path)
        arr = dcm.pixel_array

        try:
            data = apply_voi_lut(arr, dcm)
        except Exception:
            # VOI LUT ausente ou (0028,1056) não suportado: usar pixel_array com normalização
            data = np.asarray(arr, dtype=np.float64)

        data = data - data.min()
        data = data / (data.max() or 1)
        data = (data * 255).astype("uint8")
        img = Image.fromarray(data)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        _safe_print(f"Erro ao processar DICOM {dicom_path}: {e}")
        return None


def load_images_for_analysis(paths: List[str]) -> List[Image.Image]:
    """
    Carrega imagens de uma lista de caminhos (JPG, PNG, DICOM, etc.)
    para envio à IA. Retorna lista de PIL.Image em RGB.
    """
    images: List[Image.Image] = []
    raster_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    dicom_ext = {".dcm", ".dicom"}

    for path in paths:
        p = path
        if not os.path.isabs(p):
            p = os.path.join(_PROJECT_ROOT, p)
        if not os.path.exists(p):
            continue
        ext = os.path.splitext(p)[1].lower()
        try:
            if ext in dicom_ext:
                img = load_dicom_image(p)
                if img is not None:
                    images.append(img)
            elif ext in raster_ext:
                img = Image.open(p)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)
            else:
                img = Image.open(p)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)
        except Exception as e:
            _safe_print(f"Erro ao carregar {p}: {e}")

    return images


class VetAIAnalyzer:
    """Classe responsável pela comunicação com a LLM (Gemini) para laudos."""

    def __init__(self) -> None:
        self.model = genai.GenerativeModel(MODEL_NAME)

    def generate_diagnosis(self, images: List[Image.Image]) -> str:  # noqa: C901
        """
        Envia imagens para o Gemini e retorna o laudo técnico em português.
        """
        prompt = """
Analyze these veterinary radiographic/ultrasound images and write a technical report in Portuguese (Brazil).

IMPORTANT CONSIDERATIONS:
1. Consider the possibility of positional and motion artifacts
2. Consider the possibility of human errors in positioning and image labeling
3. If image quality is compromised, mention it in your findings
4. Do not invent findings that are not clearly visible

Start immediately with:
**Descrição dos Achados:**
[your detailed findings, mentioning any artifacts or positioning issues if present]

**Impressão Diagnóstica:**
[your diagnostic impression based on visible findings]

**Conclusão:**
[your conclusion]

**Recomendações:**
[your recommendations, including additional views if positioning was suboptimal]

**Referências:**
[if applicable]

CRITICAL: Your response MUST start with "**Descrição dos Achados:**" - nothing before it.
Be professional and acknowledge limitations when present.
"""

        _safe_print("Enviando imagens para análise da IA (isso pode levar alguns segundos)...")
        try:
            content: list = [prompt] + images
            response = self.model.generate_content(content)
            text = response.text.strip()

            pattern = r"\*\*Descri[çc][ãa]o dos Achados:?\*\*"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                text = text[match.start() :]
            else:
                simple = re.search(r"\*\*Descri[çc][ãa]o", text, re.IGNORECASE)
                if simple:
                    text = text[simple.start() :]

            lines = text.split("\n")
            cleaned: List[str] = []
            skip_patterns = [
                "identificação",
                "modalidade:",
                "médico veterinário",
                "data do exame:",
                "dmv",
                "especialista em",
            ]

            for line in lines:
                stripped = line.strip()
                if not cleaned and not stripped:
                    continue
                if stripped in ("---", "***", "___"):
                    continue
                if stripped.startswith("#"):
                    continue
                if "|" in stripped:
                    continue
                lower = stripped.lower()
                if any(p in lower for p in skip_patterns):
                    continue
                cleaned.append(line)

            result = "\n".join(cleaned)
            result = re.sub(r"\n{3,}", "\n\n", result)
            result = result.strip()
            return result if result else text

        except Exception as e:
            return (
                "[ERRO NA IA: Não foi possível gerar o laudo automático. "
                f"Detalhe: {str(e)}]"
            )
