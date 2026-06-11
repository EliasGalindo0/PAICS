"""
Geração de PDF de laudo veterinário (pré-visualização e exportação).
"""
import io
from typing import Any, Dict, List, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image

from utils.laudo_template import build_laudo_text


def _clean(t: str) -> str:
    """Normaliza texto para encoding latin-1 (FPDF)."""
    t = str(t) if t is not None else ""
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


def _fit_image_in_box(img: Image.Image, max_w: float, max_h: float) -> tuple[float, float]:
    """Retorna (largura_mm, altura_mm) mantendo proporção dentro da caixa."""
    w_px, h_px = img.size
    if w_px <= 0 or h_px <= 0:
        return max_w, max_h
    ar = h_px / w_px
    w_mm = max_w
    h_mm = w_mm * ar
    if h_mm > max_h:
        h_mm = max_h
        w_mm = h_mm / ar
    return w_mm, h_mm


def _add_images_grid_page(pdf: FPDF, images: List[Image.Image], cols: int = 2) -> None:
    """
    Adiciona uma única página com imagens em grade (2 por linha).
    Dimensiona todas as células para caber na página A4 sem páginas em branco.
    """
    if not images:
        return

    margin = 15.0
    page_w = 210.0
    page_h = 297.0
    usable_w = page_w - 2 * margin
    gap = 4.0
    label_h = 5.0
    row_gap = 3.0
    title_h = 10.0

    n = len(images)
    rows = (n + cols - 1) // cols
    cell_w = (usable_w - gap * (cols - 1)) / cols

    # Reserva espaço para assinatura no rodapé da mesma página
    sig_reserve = 38.0
    bottom_margin = margin + sig_reserve
    avail_h = page_h - margin - title_h - bottom_margin
    max_cell_h = (avail_h - row_gap * max(rows - 1, 0) - label_h * rows) / rows
    max_cell_h = max(max_cell_h, 25.0)

    pdf.add_page()
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, title_h, "Imagens do exame", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    start_y = pdf.get_y() + 2.0

    for idx, img in enumerate(images):
        col = idx % cols
        row = idx // cols
        cell_x = margin + col * (cell_w + gap)
        cell_y = start_y + row * (max_cell_h + label_h + row_gap)

        fit_w, fit_h = _fit_image_in_box(img, cell_w, max_cell_h)
        img_x = cell_x + (cell_w - fit_w) / 2

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pdf.image(buf, x=img_x, y=cell_y, w=fit_w, h=fit_h)

        pdf.set_xy(cell_x, cell_y + fit_h + 0.5)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(cell_w, label_h, f"Imagem {idx + 1}", align="C")


def _add_signature_block(
    pdf: FPDF,
    crmv: str = "Medica Veterinaria-CRMV SP32247",
    *,
    after_images: bool = False,
) -> None:
    """Rodapé com assinatura. after_images=True evita página extra após grade absoluta."""
    sig_h = 35.0
    if not after_images and pdf.get_y() > pdf.h - pdf.b_margin - sig_h:
        pdf.add_page()
    prev_break = pdf.auto_page_break
    prev_margin = pdf.b_margin
    pdf.set_auto_page_break(auto=False)
    pdf.set_y(-sig_h)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, "_" * 60, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, "Dra. Lais Costa Muchiutti", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.ln(2)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, crmv, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_auto_page_break(auto=prev_break, margin=prev_margin)


def gerar_pdf_laudo(
    *,
    paciente: str,
    tutor: str,
    clinica: str,
    veterinario: str,
    data_str: str,
    texto_laudo: str,
    images: Optional[List[Image.Image]] = None,
) -> bytes:
    """Gera PDF completo do laudo (cabeçalho + texto + imagens em grade + assinatura)."""
    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Paciente: {_clean(paciente)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Tutor: {_clean(tutor)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Clinica Solicitante: {_clean(clinica)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Medico(a) Veterinario(a): {_clean(veterinario)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Data: {_clean(data_str)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 5, _clean(texto_laudo))

    imgs = images or []
    if imgs:
        _add_images_grid_page(pdf, imgs, cols=2)
        _add_signature_block(pdf, after_images=True)
    else:
        _add_signature_block(pdf)

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out


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

    if image_paths:
        try:
            from ai.analyzer import load_images_for_analysis
            images = load_images_for_analysis(image_paths)
        except Exception:
            images = []
    else:
        images = []

    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "LAUDO VETERINARIO DE IMAGEM", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, _clean(texto))

    if images:
        _add_images_grid_page(pdf, images, cols=2)
        _add_signature_block(pdf, crmv="Medica Veterinaria - CRMV-XX XXXXX", after_images=True)
    else:
        _add_signature_block(pdf, crmv="Medica Veterinaria - CRMV-XX XXXXX")

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out
