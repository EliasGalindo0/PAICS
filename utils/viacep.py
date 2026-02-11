"""
Integração com a API ViaCEP para busca de endereço por CEP.
https://viacep.com.br/
"""
import re
from typing import Optional, Dict

import requests


def buscar_cep(cep: str, max_retries: int = 3) -> Optional[Dict[str, str]]:
    """
    Busca endereço pelo CEP na API ViaCEP.
    Aceita CEP com ou sem hífen (ex: 01310-100 ou 01310100).
    Retorna dict com logradouro, bairro, cidade, uf ou None se não encontrar.
    Usa retry para maior confiabilidade (API pode falhar intermitentemente).
    """
    cep_limpo = re.sub(r"\D", "", cep or "")
    if len(cep_limpo) != 8:
        return None
    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # ViaCEP retorna {"erro": true} para CEP inexistente (HTTP 200)
            if isinstance(data, dict) and data.get("erro") is True:
                return None
            if not isinstance(data, dict):
                return None
            return {
                "cep": data.get("cep", ""),
                "logradouro": data.get("logradouro", ""),
                "bairro": data.get("bairro", ""),
                "cidade": data.get("localidade", ""),
                "uf": data.get("uf", ""),
            }
        except Exception:
            if attempt == max_retries - 1:
                return None
            import time
            time.sleep(0.5 * (attempt + 1))
    return None
