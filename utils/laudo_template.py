"""
Template e formatação do laudo veterinário para pré-visualização e exportação.
"""
from datetime import datetime
from typing import Dict, Any, List


def _fmt(s: Any) -> str:
    if s is None or s == "":
        return "—"
    return str(s).strip()


def _fmt_date(d: Any) -> str:
    from datetime import date
    if d is None:
        return datetime.now().strftime("%d/%m/%Y")
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, date) and not isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, str) and d:
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00")[:19])
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return d
    return "—"


def build_laudo_text(data: Dict[str, Any], incluir_cabecalho: bool = True) -> str:
    """
    Gera o texto formatado do laudo a partir dos dados do formulário.
    Usado na pré-visualização em tempo real e na exportação PDF.
    """
    paciente = _fmt(data.get("paciente"))
    especie = _fmt(data.get("especie"))
    idade = _fmt(data.get("idade"))
    raca = _fmt(data.get("raca"))
    sexo = _fmt(data.get("sexo"))
    tutor = _fmt(data.get("tutor"))
    clinica = _fmt(data.get("clinica"))
    medico = _fmt(data.get("medico_veterinario_solicitante"))
    regiao = _fmt(data.get("regiao_estudo"))
    suspeita = _fmt(data.get("suspeita_clinica"))
    plantao = _fmt(data.get("plantao"))
    historico = _fmt(data.get("historico_clinico"))
    tipo_exame = _fmt(data.get("tipo_exame"))
    data_exame = _fmt_date(data.get("data") or data.get("data_exame"))

    lines: List[str] = []
    if incluir_cabecalho:
        lines.append("LAUDO VETERINÁRIO DE IMAGEM")
        lines.append("")
    lines.append(f"Paciente: {paciente}")
    lines.append(f"Espécie: {especie}")
    lines.append(f"Idade: {idade}")
    lines.append(f"Raça: {raca}")
    lines.append(f"Sexo: {sexo}")
    lines.append(f"Tutor(a): {tutor}")
    lines.append(f"Clínica Veterinária Solicitante: {clinica}")
    lines.append(f"Médico(a) Veterinário(a) Solicitante: {medico}")
    lines.append(f"Região de estudo: {regiao}")
    lines.append(f"Suspeita clínica: {suspeita}")
    lines.append(f"Plantão: {plantao}")
    lines.append(f"Tipo de exame: {tipo_exame}")
    lines.append(f"Data: {data_exame}")
    lines.append("")
    lines.append("Histórico clínico:")
    lines.append(historico if historico != "—" else "(não informado)")
    lines.append("")
    lines.append("—")
    lines.append("Resultado / Laudo (será preenchido pelo médico responsável)")
    lines.append("—")
    return "\n".join(lines)


def dados_from_requisicao(req: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai dicionário de dados do formulário a partir de uma requisição."""
    return {
        "paciente": req.get("paciente", ""),
        "especie": req.get("especie", ""),
        "idade": req.get("idade", ""),
        "raca": req.get("raca", ""),
        "sexo": req.get("sexo", ""),
        "tutor": req.get("tutor", ""),
        "clinica": req.get("clinica", ""),
        "medico_veterinario_solicitante": req.get("medico_veterinario_solicitante", ""),
        "regiao_estudo": req.get("regiao_estudo", ""),
        "suspeita_clinica": req.get("suspeita_clinica", ""),
        "plantao": req.get("plantao", ""),
        "historico_clinico": req.get("historico_clinico", "") or req.get("observacoes", ""),
        "tipo_exame": req.get("tipo_exame", "raio-x"),
        "data": req.get("data_exame") or req.get("created_at"),
    }
