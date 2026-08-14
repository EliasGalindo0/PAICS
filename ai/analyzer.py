"""
Analisador de imagens veterinárias com OpenAI (visão + texto).
Usado pela API FastAPI, learning system e scripts CLI.
Suporta imagens por path (filesystem) ou por ID do GridFS (MongoDB).
"""
from __future__ import annotations

import base64
import io
import os
import re
import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"), override=True)


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


def _pil_to_data_url(img: Image.Image) -> str:
    """Converte PIL Image RGB para data URL JPEG (bem menor que PNG na OpenAI)."""
    w, h = img.size
    max_side = 1536
    longest = max(w, h) or 1
    if longest > max_side:
        scale = max_side / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


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
            data = np.asarray(arr, dtype=np.float32)

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


def _load_image_from_bytes(data: bytes, filename_hint: str = "imagem") -> Optional[Image.Image]:
    """Carrega PIL Image a partir de bytes (GridFS ou buffer)."""
    try:
        ext = os.path.splitext(filename_hint)[1].lower()
        dicom_ext = {".dcm", ".dicom"}
        buf = io.BytesIO(data)
        if ext in dicom_ext:
            try:
                import numpy as np
                import pydicom
                from pydicom.pixel_data_handlers.util import apply_voi_lut
                dcm = pydicom.dcmread(buf)
                arr = dcm.pixel_array
                try:
                    data_arr = apply_voi_lut(arr, dcm)
                except Exception:
                    data_arr = np.asarray(arr, dtype=np.float32)
                data_arr = data_arr - data_arr.min()
                data_arr = data_arr / (data_arr.max() or 1)
                data_arr = (data_arr * 255).astype("uint8")
                img = Image.fromarray(data_arr)
            except Exception:
                return None
        else:
            img = Image.open(buf).copy()
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        _safe_print(f"Erro ao carregar imagem de bytes ({filename_hint}): {e}")
        return None


def load_images_for_analysis(refs: List[str]) -> List[Image.Image]:
    """
    Carrega imagens de uma lista de referências.
    Cada ref pode ser: ID do GridFS (24 hex) ou path no filesystem (legado).
    Retorna lista de PIL.Image em RGB.
    """
    images: List[Image.Image] = []
    raster_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    dicom_ext = {".dcm", ".dicom"}

    for ref in refs:
        ref = (ref or "").strip()
        if not ref:
            continue
        try:
            from database.image_storage import get_image_bytes_and_filename, is_gridfs_ref
            if is_gridfs_ref(ref):
                result = get_image_bytes_and_filename(ref)
                if result:
                    data, filename = result
                    img = _load_image_from_bytes(data, filename)
                    if img is not None:
                        images.append(img)
                continue
            p = ref
            if not os.path.isabs(p):
                p = os.path.join(_PROJECT_ROOT, p)
            if not os.path.exists(p):
                continue
            ext = os.path.splitext(p)[1].lower()
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
            _safe_print(f"Erro ao carregar {ref}: {e}")

    return images


class VetAIAnalyzer:
    """Comunicação com a API OpenAI (visão) para geração de laudos."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or api_key in ("SUA_API_KEY_AQUI", "sua_chave_aqui"):
            raise RuntimeError(
                "OPENAI_API_KEY não configurada. Defina a variável de ambiente no Railway ou .env."
            )
        timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "180"))
        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
        self.fallback_model_name = os.getenv("OPENAI_FALLBACK_MODEL_NAME", "").strip() or None
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))

    def _build_message_content(self, prompt: str, images: List[Image.Image]) -> list:
        content: list = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": _pil_to_data_url(img), "detail": "auto"},
            })
        return content

    def _generate_with_fallback(self, prompt: str, images: List[Image.Image], context: str) -> str:
        """Chama OpenAI com modelo principal; em falha, tenta fallback (se configurado)."""
        from utils.observability import log_api, log_api_error

        models = [self.model_name]
        if self.fallback_model_name and self.fallback_model_name != self.model_name:
            models.append(self.fallback_model_name)

        last_error: Optional[Exception] = None
        message_content = self._build_message_content(prompt, images)

        for idx, model in enumerate(models):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": message_content}],
                    max_tokens=self.max_tokens,
                )
                text = (response.choices[0].message.content or "").strip()
                if text:
                    label = "OpenAI fallback OK" if idx > 0 else "OpenAI OK"
                    try:
                        log_api.warning("%s | model=%s | context=%s", label, model, context or "(nenhum)")
                    except Exception:
                        pass
                return text
            except Exception as e:
                last_error = e
                src = "OpenAI.chat.completions.fallback" if idx > 0 else "OpenAI.chat.completions"
                log_api_error(src, e, context=f"{context} | model={model}")

        if last_error:
            raise last_error
        return ""

    def generate_diagnosis(
        self,
        images: List[Image.Image],
        paciente_info: Optional[Dict[str, str]] = None,
    ) -> str:  # noqa: C901
        """
        Envia imagens para a OpenAI e retorna o laudo técnico em português.
        """
        especie = (paciente_info or {}).get("especie", "Não informado")
        raca = (paciente_info or {}).get("raca", "Não informado")
        idade = (paciente_info or {}).get("idade", "Não informado")
        sexo = (paciente_info or {}).get("sexo", "Não informado")
        historico = (paciente_info or {}).get("historico_clinico", "") or (
            paciente_info or {}).get("observacoes", "") or "Não informado"
        suspeita_clinica = (paciente_info or {}).get("suspeita_clinica", "Não informado")
        regiao_estudo = (paciente_info or {}).get("regiao_estudo", "Não informado")
        obs_adicionais = (paciente_info or {}).get("observacoes_adicionais_usuario", "").strip()

        template_mascara = ""
        if regiao_estudo and regiao_estudo.strip():
            try:
                from utils.template_mascaras import get_template_content_multi
                template_mascara = get_template_content_multi(regiao_estudo) or ""
            except Exception:
                pass

        prompt = f"""
You are a specialist veterinary radiologist. Generate a direct, concise technical report in Portuguese (Brazil).

PATIENT CONTEXT:
- Species: {especie}
- Breed: {raca}
- Age: {idade}
- Sex: {sexo}
- Clinical History: {historico}
- Clinical Suspicion: {suspeita_clinica}
- Study Region: {regiao_estudo}
"""
        if template_mascara:
            prompt += f"""
REPORT STRUCTURE (MANDATORY – your response MUST follow this template exactly):

{template_mascara}

INSTRUCTIONS:
- Use the EXACT section names and structure from the template above (e.g. ANÁLISE RADIOGRÁFICA, IMPRESSÃO RADIOGRÁFICA/DIAGNÓSTICA).
- For each bullet item in the template, describe the finding according to the images. Adapt to actual findings (normal/abnormal).
- Your response MUST start IMMEDIATELY with the first section header from the template (e.g. "REGIÃO:" or "ANÁLISE RADIOGRÁFICA:").
- Write in bullet points, one finding per line. Be objective and brief. Use veterinary radiological terminology in Portuguese (Brazil).

"""
        else:
            prompt += """
REPORT STRUCTURE (MANDATORY – all sections in BULLET/TOPIC format, one item per line):

**Descrição dos Achados:**
- START with the most relevant or important findings (abnormal or clinically significant findings); then describe the rest, including structures within normal limits.
- Write ONLY in bullet points (topics), one finding per line.
- Normal findings: one short line (e.g. "- Sistema esquelético: dentro da normalidade").
- Abnormal or relevant findings: one bullet each with the essential detail.
- Do NOT write long descriptive paragraphs.

**Impressão Diagnóstica:**
- Bullet points only (differential diagnoses or main impression, one per line).

**Conclusão:**
- Bullet points only (main conclusions, one per line).

**Recomendações:**
- Bullet points only, if applicable (additional exams, follow-up). Omit if none.

CRITICAL:
- Your response MUST start IMMEDIATELY with "**Descrição dos Achados:**"
- No preamble or introduction.
- Keep the report short: avoid lengthy descriptions of normal findings.

"""
        if obs_adicionais:
            prompt += f"""
ADDITIONAL NOTES FROM THE REFERRING CLIENT (consider these to improve report accuracy; the client may have sent corrections or remembered important details):
{obs_adicionais}

"""
        prompt += """
STYLE: Be objective and brief. Do NOT write long paragraphs. For structures within normal limits, state briefly. Focus detail only on relevant or abnormal findings. Use veterinary radiological terminology in Portuguese (Brazil).

"""
        _safe_print("Enviando imagens para análise da IA (isso pode levar alguns segundos)...")
        try:
            text = self._generate_with_fallback(prompt, images, context="laudo principal")

            pattern = r"(\*\*Descri[çc][ãa]o dos Achados:?\*\*|AN[ÁA]LISE RADIOGR[ÁA]FICA:?|REGI[ÁA]O:?)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                text = text[match.start():]
            else:
                simple = re.search(
                    r"(\*\*Descri[çc][ãa]o|AN[ÁA]LISE RADIOGR[ÁA]FICA|REGI[ÁA]O)", text, re.IGNORECASE
                )
                if simple:
                    text = text[simple.start():]

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
            from utils.observability import log_api_error
            log_api_error("OpenAI.generate_diagnosis", e, context="laudo principal")
            return (
                "[ERRO NA IA: Não foi possível gerar o laudo automático. "
                f"Detalhe: {str(e)}]"
            )

    def generate_diagnosis_with_corrections(
        self,
        images: List[Image.Image],
        paciente_info: Optional[Dict[str, str]],
        correcoes_texto: str,
        laudo_anterior: str,
    ) -> str:
        """Gera novo laudo incorporando correções do especialista."""
        especie = (paciente_info or {}).get("especie", "Não informado")
        raca = (paciente_info or {}).get("raca", "Não informado")
        idade = (paciente_info or {}).get("idade", "Não informado")
        sexo = (paciente_info or {}).get("sexo", "Não informado")
        historico = (paciente_info or {}).get("historico_clinico", "") or (
            paciente_info or {}).get("observacoes", "") or "Não informado"
        suspeita = (paciente_info or {}).get("suspeita_clinica", "Não informado")
        regiao = (paciente_info or {}).get("regiao_estudo", "Não informado")

        prompt = f"""You are a specialist veterinary radiologist. The specialist has reviewed a previous report and provided corrections. Generate a NEW corrected report in Portuguese (Brazil) that incorporates these corrections.

CORREÇÕES DO ESPECIALISTA:
{correcoes_texto}

LAUDO ANTERIOR (tinha erros):
{laudo_anterior}

DADOS DO PACIENTE:
- Espécie: {especie}
- Raça: {raca}
- Idade: {idade}
- Sexo: {sexo}
- Histórico clínico: {historico}
- Suspeita clínica: {suspeita}
- Região de estudo: {regiao}

Generate a new report that fixes the errors indicated by the specialist. Keep the report direct and in bullet/topic format: Descrição dos Achados, Impressão Diagnóstica and Conclusão in topics (one per line). In Descrição dos Achados, start with the most relevant or important findings (abnormal or significant), then the rest. Do not write long paragraphs. Your response MUST start immediately with "**Descrição dos Achados:**". Use professional veterinary terminology in Portuguese (Brazil).
"""
        _safe_print("Gerando laudo com correções do especialista...")
        try:
            text = self._generate_with_fallback(prompt, images, context="laudo com correções")
            pattern = r"\*\*Descri[çc][ãa]o dos Achados:?\*\*"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                text = text[match.start():]
            return re.sub(r"\n{3,}", "\n\n", text).strip() or text
        except Exception as e:
            from utils.observability import log_api_error
            log_api_error("OpenAI.generate_diagnosis_with_corrections", e, context="laudo com correções")
            return (
                "[ERRO NA IA: Não foi possível gerar o laudo. "
                f"Detalhe: {str(e)}]"
            )
