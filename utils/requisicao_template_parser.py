"""
Extrai campos de requisição a partir do template de texto enviado pelas clínicas.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from utils.template_mascaras import REGIAO_ALIASES, REGIAO_TO_TEMPLATE, _normalize

_ESPECIE_CANONICA = {
    "CANINO": "Canino",
    "FELINO": "Felino",
    "AVE": "Ave",
    "AVES": "Ave",
    "SILVESTRE": "Silvestre",
    "EQUINO": "Silvestre",
    "BOVINO": "Silvestre",
    "ROEDOR": "Silvestre",
    "ROEDORES": "Silvestre",
    "EXOTICO": "Silvestre",
    "EXÓTICO": "Silvestre",
}

_FIELD_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("data_exame", re.compile(r"^data\s*:\s*(.+)$", re.I)),
    ("paciente", re.compile(r"^(?:nome\s+do\s+)?paciente\s*:\s*(.+)$", re.I)),
    ("especie", re.compile(r"^esp[eé]cie\s*:\s*(.+)$", re.I)),
    ("idade", re.compile(r"^idade\s*:\s*(.+)$", re.I)),
    ("raca", re.compile(r"^ra[cç]a\s*:\s*(.+)$", re.I)),
    ("tutor", re.compile(r"^tutor\s*(?:\([aã]\))?\s*:\s*(.+)$", re.I)),
    (
        "medico_veterinario_solicitante",
        re.compile(
            r"^(?:m\.?\s*v\.?\s*(?:solicitante)?|m[eé]dico\s*(?:\(a\)\s*)?veterin[aá]ri[oa]\s*(?:solicitante)?)\s*:\s*(.+)$",
            re.I,
        ),
    ),
    (
        "regiao_estudo",
        re.compile(r"^regi[aã]o\s*(?:de\s+estudo)?\s*:\s*(.+)$", re.I),
    ),
    ("suspeita_clinica", re.compile(r"^suspeita\s*(?:cl[ií]nica)?\s*:\s*(.+)$", re.I)),
    (
        "historico_clinico",
        re.compile(
            r"^(?:hist[oó]rico\s*(?:cl[ií]nico)?|observa[cç][oõ]es?\s*(?:cl[ií]nicas?)?)\s*:\s*(.+)$",
            re.I,
        ),
    ),
    ("plantao", re.compile(r"^plant[aã]o\s*:\s*(.+)$", re.I)),
    ("sedacao", re.compile(r"^seda[cç][aã]o\s*:\s*(.+)$", re.I)),
]


def _strip_line(line: str) -> str:
    line = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0000FE00-\U0000FEFF]",
        "",
        line,
    )
    for ch in ("🔹", "🔷", "▪", "•", "◆", "◇", "️"):
        line = line.replace(ch, "")
    return line.strip()


def _parse_data_br(value: str) -> Optional[str]:
    value = value.strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if not m:
        return None
    d, mo, y = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _normalize_especie(value: str) -> str:
    key = _normalize(value)
    return _ESPECIE_CANONICA.get(key, value.strip().capitalize())


def _normalize_sim_nao(value: str) -> str:
    v = value.strip().lower()
    if v in ("sim", "s", "yes"):
        return "Sim"
    if v in ("nao", "não", "n", "no"):
        return "Não"
    return value.strip()


def _resolve_regioes(regiao_text: str) -> Tuple[List[str], str]:
    if not regiao_text or not regiao_text.strip():
        return [], ""

    matched: List[str] = []
    unmatched: List[str] = []
    parts = re.split(r"\s+e\s+|,|\s*/\s*|\s+\+\s+", regiao_text, flags=re.I)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        p_norm = _normalize(part)
        found: Optional[str] = None

        for valor, _ in REGIAO_TO_TEMPLATE:
            if _normalize(valor) == p_norm:
                found = valor
                break
        if not found:
            for alias, canon in REGIAO_ALIASES:
                if _normalize(alias) == p_norm:
                    found = canon
                    break
        if not found:
            for valor, _ in REGIAO_TO_TEMPLATE:
                v_norm = _normalize(valor)
                if p_norm in v_norm or v_norm in p_norm:
                    found = valor
                    break
        if not found:
            for alias, canon in REGIAO_ALIASES:
                a_norm = _normalize(alias)
                if p_norm in a_norm or a_norm in p_norm:
                    found = canon
                    break

        if found and found not in matched:
            matched.append(found)
        elif not found:
            unmatched.append(part)

    return matched, ", ".join(unmatched)


def parse_requisicao_template(texto: str) -> Dict[str, Any]:
    """
    Extrai campos do template de requisição colado pela administradora.

    Returns:
        dict com campos do formulário e lista de campos reconhecidos.
    """
    raw: Dict[str, str] = {}
    for line in texto.splitlines():
        clean = _strip_line(line)
        if not clean or clean.lower().startswith("dados para laudo"):
            continue
        for field, pattern in _FIELD_PATTERNS:
            m = pattern.match(clean)
            if m:
                raw[field] = m.group(1).strip()
                break

    regioes, regiao_outra = _resolve_regioes(raw.get("regiao_estudo", ""))
    data_iso = _parse_data_br(raw.get("data_exame", "")) if raw.get("data_exame") else None
    plantao = _normalize_sim_nao(raw["plantao"]) if raw.get("plantao") else ""
    sedacao = _normalize_sim_nao(raw["sedacao"]) if raw.get("sedacao") else ""

    campos_encontrados = [k for k in raw if raw[k]]
    if regioes:
        campos_encontrados.append("regioes_estudo")
    if regiao_outra:
        campos_encontrados.append("regiao_estudo_outra")

    return {
        "paciente": raw.get("paciente", ""),
        "tutor": raw.get("tutor", ""),
        "especie": _normalize_especie(raw["especie"]) if raw.get("especie") else "",
        "idade": raw.get("idade", ""),
        "raca": raw.get("raca", ""),
        "medico_veterinario_solicitante": raw.get("medico_veterinario_solicitante", ""),
        "regioes_estudo": regioes,
        "regiao_estudo_outra": regiao_outra,
        "suspeita_clinica": raw.get("suspeita_clinica", ""),
        "historico_clinico": raw.get("historico_clinico", ""),
        "data_exame": data_iso or "",
        "plantao": plantao,
        "sedacao": sedacao,
        "campos_encontrados": campos_encontrados,
    }
