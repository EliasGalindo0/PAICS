from utils.requisicao_template_parser import parse_requisicao_template

TEMPLATE = """
Dados para laudo

Data: 10/06/2026

🔹 Nome do paciente: Xuxa
🔹 Espécie: Canino
🔹 Idade: 12 anos
🔹 Raça: Srd
🔹Tutor(a): Valdemir Boleti
🔹 M.V. Solicitante: Jeniffer Nunes
🔹 Região de estudo: Tórax e MTE
🔹️Suspeita: metástase pulmonar e comprometimento ósseo no MTE
🔹️ Plantão: não
🔷 Sedação: não
"""


def test_parse_template_completo():
    r = parse_requisicao_template(TEMPLATE)
    assert r["paciente"] == "Xuxa"
    assert r["tutor"] == "Valdemir Boleti"
    assert r["especie"] == "Canino"
    assert r["idade"] == "12 anos"
    assert r["raca"] == "Srd"
    assert r["medico_veterinario_solicitante"] == "Jeniffer Nunes"
    assert "REGIÃO TÓRAX" in r["regioes_estudo"]
    assert "MTE" in r["regiao_estudo_outra"]
    assert "metástase pulmonar" in r["suspeita_clinica"]
    assert r["data_exame"] == "2026-06-10"
    assert r["plantao"] == "Não"
    assert "Plantão: Não" in r["historico_clinico"]
    assert "Sedação: Não" in r["historico_clinico"]
    assert len(r["campos_encontrados"]) >= 8


def test_parse_template_vazio():
    r = parse_requisicao_template("")
    assert r["paciente"] == ""
    assert r["regioes_estudo"] == []
