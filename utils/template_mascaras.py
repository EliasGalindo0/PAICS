"""
Máscaras (templates) de laudo por região de estudo.
Mapeia regiões de estudo para PDFs em templates/ e extrai o conteúdo
para guiar a geração do laudo pela IA.
"""
import os
import re
from typing import Optional, List, Tuple

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(_PROJECT_ROOT, "templates")

# Mapeamento: valor do select (regiao_estudo) -> nome do arquivo PDF
# O valor armazenado deve corresponder exatamente para match
REGIAO_TO_TEMPLATE: List[Tuple[str, str]] = [
    ("PELVE", "PELVE.pdf"),
    ("REGIÃO ABDOME", "REGIÃO ABDOME.pdf"),
    ("REGIÃO ABDOME GESTAÇÃO", "REGIÃO ABDOME GESTAÇÃO.pdf"),
    ("REGIÃO CERVICAL - TECIDOS MOLES", "REGIÃO CERVICAL - TECIDOS MOLES.pdf"),
    ("REGIÃO COLUNA VERTEBRAL", "REGIÃO COLUNA VERTEBRAL.pdf"),
    ("REGIÃO CRÂNIO", "REGIÃO CRÂNIO.pdf"),
    ("REGIÃO MEMBRO ANTERIOR", "REGIÃO MEMBRO ANTERIOR.pdf"),
    ("REGIÃO MEMBRO POSTERIOR", "REGIÃO MEMBRO POSTERIOR.pdf"),
    ("REGIÃO TÓRAX", "REGIÃO TÓRAX.pdf"),
]

# Aliases para match flexível (região digitada livremente -> valor canônico)
# Ex: "Pelve", "pelve", "PELVE" -> PELVE
REGIAO_ALIASES: List[Tuple[str, str]] = [
    ("PELVE", "PELVE"),
    ("PELVIS", "PELVE"),
    ("PÉLVIS", "PELVE"),
    ("ABDOME", "REGIÃO ABDOME"),
    ("ABDÔMEN", "REGIÃO ABDOME"),
    ("ABDOMEN", "REGIÃO ABDOME"),
    ("ABDOME GESTAÇÃO", "REGIÃO ABDOME GESTAÇÃO"),
    ("ABDÔMEN GESTAÇÃO", "REGIÃO ABDOME GESTAÇÃO"),
    ("ABDOME GESTACAO", "REGIÃO ABDOME GESTAÇÃO"),
    ("CERVICAL", "REGIÃO CERVICAL - TECIDOS MOLES"),
    ("CERVICAL TECIDOS MOLES", "REGIÃO CERVICAL - TECIDOS MOLES"),
    ("COLUNA", "REGIÃO COLUNA VERTEBRAL"),
    ("COLUNA VERTEBRAL", "REGIÃO COLUNA VERTEBRAL"),
    ("CRANIO", "REGIÃO CRÂNIO"),
    ("CRÂNIO", "REGIÃO CRÂNIO"),
    ("MEMBRO ANTERIOR", "REGIÃO MEMBRO ANTERIOR"),
    ("MEMBROS ANTERIORES", "REGIÃO MEMBRO ANTERIOR"),
    ("MEMBRO POSTERIOR", "REGIÃO MEMBRO POSTERIOR"),
    ("MEMBROS POSTERIORES", "REGIÃO MEMBRO POSTERIOR"),
    ("TORAX", "REGIÃO TÓRAX"),
    ("TÓRAX", "REGIÃO TÓRAX"),
]


def _normalize(s: str) -> str:
    """Normaliza texto para comparação (remove acentos, lowercase, espaços)."""
    if not s:
        return ""
    s = s.strip().upper()
    # Normalizar acentos
    replacements = [
        ("Á", "A"), ("À", "A"), ("Â", "A"), ("Ã", "A"),
        ("É", "E"), ("Ê", "E"),
        ("Í", "I"),
        ("Ó", "O"), ("Ô", "O"), ("Õ", "O"),
        ("Ú", "U"), ("Ç", "C"),
    ]
    for a, b in replacements:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def get_template_path_for_regiao(regiao_estudo: str) -> Optional[str]:
    """
    Retorna o caminho do arquivo PDF do template para a região de estudo,
    ou None se não houver template correspondente.

    Args:
        regiao_estudo: Região informada no cadastro (ex: "PELVE", "REGIÃO TÓRAX")

    Returns:
        Caminho absoluto do PDF ou None
    """
    if not regiao_estudo or not regiao_estudo.strip():
        return None

    regiao_norm = _normalize(regiao_estudo)

    # Match exato no mapeamento
    for valor, arquivo in REGIAO_TO_TEMPLATE:
        if _normalize(valor) == regiao_norm:
            path = os.path.join(TEMPLATES_DIR, arquivo)
            if os.path.isfile(path):
                return path
            return None

    # Match por alias
    for alias, valor_canonico in REGIAO_ALIASES:
        if _normalize(alias) == regiao_norm:
            for v, arquivo in REGIAO_TO_TEMPLATE:
                if v == valor_canonico:
                    path = os.path.join(TEMPLATES_DIR, arquivo)
                    if os.path.isfile(path):
                        return path
                    return None

    # Match parcial (ex: "regiao torax" contém "torax")
    for valor, arquivo in REGIAO_TO_TEMPLATE:
        v_norm = _normalize(valor)
        if v_norm in regiao_norm or regiao_norm in v_norm:
            path = os.path.join(TEMPLATES_DIR, arquivo)
            if os.path.isfile(path):
                return path

    return None


def get_template_content(regiao_estudo: str) -> Optional[str]:
    """
    Extrai o texto do template PDF da região de estudo.
    Usado para injetar no prompt da IA como máscara/estrutura do laudo.

    Returns:
        Texto extraído do PDF ou None
    """
    path = get_template_path_for_regiao(regiao_estudo)
    if not path:
        return None

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text_parts = []
        for page in doc:
            t = page.get_text()
            if t and t.strip():
                text_parts.append(t.strip())
        doc.close()
        return "\n\n".join(text_parts) if text_parts else None
    except Exception:
        return None


def list_regioes_estudo() -> List[dict]:
    """
    Retorna lista de regiões de estudo disponíveis para o select no formulário.
    Cada item tem: { value, label }
    """
    return [
        {"value": "", "label": "Selecione (sem máscara)"},
        *[{"value": v, "label": v} for v, _ in REGIAO_TO_TEMPLATE],
        {"value": "__outra__", "label": "Outra (informar)"},
    ]
