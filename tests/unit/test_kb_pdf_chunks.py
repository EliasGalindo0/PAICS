from knowledge_base.pdf_text import chunk_text


def test_chunk_texto_curto_nao_divide():
    assert chunk_text("hello world") == ["hello world"]


def test_chunk_texto_vazio():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_texto_longo_respeita_tamanho():
    text = ("palavra " * 800).strip()
    chunks = chunk_text(text, max_chars=180, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 180 for c in chunks)
    joined = " ".join(chunks)
    assert "palavra" in joined


def test_chunk_nao_entra_em_loop():
    text = "a" * 5000
    chunks = chunk_text(text, max_chars=100, overlap=10)
    assert 40 <= len(chunks) <= 60
