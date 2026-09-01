"""Extração e fatiamento de texto de PDFs da knowledge base."""
from typing import List, Tuple

# MiniLM do Chroma trunca ~256 tokens; fatias curtas evitam OOM em livros.
CHUNK_CHARS = 1800
CHUNK_OVERLAP = 200
MIN_TEXT_CHARS = 200
MONGO_PREVIEW_CHARS = 80_000


def chunk_text(text: str, max_chars: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide texto em trechos com sobreposição para embeddings."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    n = len(cleaned)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            cut = cleaned.rfind(" ", start + (max_chars // 2), end)
            if cut > start:
                end = cut
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_pdf_text(file_path: str) -> Tuple[str, int]:
    """Extrai texto de todas as páginas. Retorna (texto, n_paginas)."""
    import fitz

    doc = fitz.open(file_path)
    try:
        n_pages = doc.page_count
        parts: List[str] = []
        for page in doc:
            page_text = (page.get_text("text") or "").strip()
            if page_text:
                parts.append(page_text)
        return "\n\n".join(parts), n_pages
    finally:
        doc.close()
