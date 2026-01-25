"""
Geração de PDF de laudo veterinário (pré-visualização e exportação).
"""
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from utils.laudo_template import build_laudo_text


def _clean(t: str) -> str:
    """Normaliza texto para encoding latin-1 (FPDF)."""
    for a, b in [
        ("'", "'"), ("'", "'"), (""", '"'), (""", '"'),
        ("—", "-"), ("–", "-"), ("…", "..."), ("°", " graus"),
    ]:
        t = t.replace(a, b)
    t = t.replace("**", "")
    try:
        t.encode("latin-1")
    except UnicodeEncodeError:
        import unicodedata
        t = unicodedata.normalize("NFKD", t).encode("latin-1", "ignore").decode("latin-1")
    return t


def gerar_pdf_preview(
    form_data: Dict[str, Any],
    image_paths: Optional[List[str]] = None,
) -> bytes:
    """
    Gera PDF de pré-visualização do laudo a partir dos dados do formulário
    e opcionalmente das imagens anexadas.
    """
    image_paths = image_paths or []
    texto = build_laudo_text(form_data, incluir_cabecalho=False)

    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "LAUDO VETERINARIO DE IMAGEM", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, _clean(texto))

    if image_paths:
        try:
            from ai.analyzer import load_images_for_analysis
            images = load_images_for_analysis(image_paths)
        except Exception:
            images = []
    else:
        images = []

    if images:
        pdf.add_page()
        for i, img in enumerate(images):
            w_px, h_px = img.size
            ar = h_px / w_px
            w_mm, h_mm = 180, min(180 * ar, 220)
            if pdf.get_y() + h_mm > 267:
                pdf.add_page()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            pdf.image(buf, w=w_mm, h=h_mm)
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 6, f"Imagem {i + 1}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            pdf.ln(4)

    pdf.set_y(-35)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, "_" * 60, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, "Dra. Lais Costa Muchiutti", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.ln(2)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "Medica Veterinaria - CRMV-XX XXXXX", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out
