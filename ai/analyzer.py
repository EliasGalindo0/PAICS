"""
Analisador de imagens veterinárias com Gemini (LLM).
Usado pelo user_dashboard, admin_dashboard e main sem depender de PyMuPDF/docx.
"""
from __future__ import annotations

import os
import re
import sys
from typing import List, Optional, Dict

import warnings

from dotenv import load_dotenv
from PIL import Image

with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
API_KEY = os.getenv("GOOGLE_API_KEY", "SUA_API_KEY_AQUI")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
genai.configure(api_key=API_KEY)


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
            # VOI LUT ausente ou (0028,1056) não suportado: usar pixel_array com normalização
            data = np.asarray(arr, dtype=np.float64)

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


def load_images_for_analysis(paths: List[str]) -> List[Image.Image]:
    """
    Carrega imagens de uma lista de caminhos (JPG, PNG, DICOM, etc.)
    para envio à IA. Retorna lista de PIL.Image em RGB.
    """
    images: List[Image.Image] = []
    raster_ext = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    dicom_ext = {".dcm", ".dicom"}

    for path in paths:
        p = path
        if not os.path.isabs(p):
            p = os.path.join(_PROJECT_ROOT, p)
        if not os.path.exists(p):
            continue
        ext = os.path.splitext(p)[1].lower()
        try:
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
            _safe_print(f"Erro ao carregar {p}: {e}")

    return images


class VetAIAnalyzer:
    """Classe responsável pela comunicação com a LLM (Gemini) para laudos."""

    def __init__(self) -> None:
        self.model = genai.GenerativeModel(MODEL_NAME)

    def generate_diagnosis(
        self,
        images: List[Image.Image],
        paciente_info: Optional[Dict[str, str]] = None
    ) -> str:  # noqa: C901
        """
        Envia imagens para o Gemini e retorna o laudo técnico em português.

        Args:
            images: Lista de imagens PIL para análise
            paciente_info: Dicionário com informações do paciente (especie, raca, idade, sexo, 
                          historico_clinico, suspeita_clinica, regiao_estudo)
        """
        # Extrair informações do paciente ou usar valores padrão
        especie = (paciente_info or {}).get("especie", "Não informado")
        raca = (paciente_info or {}).get("raca", "Não informado")
        idade = (paciente_info or {}).get("idade", "Não informado")
        sexo = (paciente_info or {}).get("sexo", "Não informado")
        historico = (paciente_info or {}).get("historico_clinico", "") or (
            paciente_info or {}).get("observacoes", "") or "Não informado"
        suspeita_clinica = (paciente_info or {}).get("suspeita_clinica", "Não informado")
        regiao_estudo = (paciente_info or {}).get("regiao_estudo", "Não informado")

        prompt = f"""
You are a specialist veterinary radiologist analyzing diagnostic images. Generate a comprehensive technical report in Portuguese (Brazil).

PATIENT CONTEXT (USE THIS INFORMATION TO INFORM YOUR ANALYSIS):
- Species: {especie}
- Breed: {raca}
- Age: {idade}
- Sex: {sexo}
- Clinical History: {historico}
- Clinical Suspicion: {suspeita_clinica}
- Study Region: {regiao_estudo}

IMPORTANT: Consider the patient's species, breed, age, and clinical history when analyzing the images. Correlate your findings with the clinical suspicion and study region requested. Use breed-specific anatomical knowledge and age-appropriate normal variations in your interpretation.

IMAGE ANALYSIS GUIDELINES:

1. TECHNICAL QUALITY ASSESSMENT:
   - Evaluate positioning accuracy (anatomical landmarks, symmetry, centering)
   - Identify motion artifacts (blur, double contours, loss of detail)
   - Assess exposure parameters (penetration, contrast, sharpness)
   - Note any technical limitations affecting interpretation

2. SYSTEMATIC EVALUATION:
   - Analyze the requested anatomical region systematically
   - Compare with normal anatomical patterns for the species, breed, and age
   - Identify any deviations from expected anatomy
   - Correlate findings with clinical history and suspicion

3. DIAGNOSTIC INTEGRITY:
   - Only report findings that are clearly visible and reproducible
   - Use appropriate veterinary radiological terminology
   - Distinguish between definitive findings and tentative observations
   - Acknowledge when findings are equivocal or require additional views

4. ARTIFACT RECOGNITION:
   - Positioning artifacts: rotation, obliquity, insufficient coverage
   - Motion artifacts: respiratory motion, patient movement
   - Equipment artifacts: grid lines, markers, foreign objects
   - Labeling errors: incorrect side markers, mislabeled projections

5. CONTEXTUAL INTERPRETATION:
   - Consider breed-specific anatomical variations
   - Account for age-related changes (pediatric vs. geriatric)
   - Integrate clinical history into differential diagnoses
   - Recognize incidental findings vs. clinically significant pathology

REPORT STRUCTURE (MANDATORY):

**Descrição dos Achados:**
[Provide detailed, systematic description of visible structures. Start with technical quality assessment if relevant. Describe normal anatomy first, then any abnormalities. Mention specific measurements when applicable. Note any artifacts or limitations.]

**Impressão Diagnóstica:**
[Based on the findings, provide your diagnostic impression. List differential diagnoses in order of likelihood. Correlate with clinical suspicion. If findings are non-specific, state this clearly.]

**Conclusão:**
[Concise summary of the main findings and their clinical significance. State if the study is limited or inconclusive due to technical factors.]

**Recomendações:**
[Suggest additional imaging views if positioning was suboptimal. Recommend complementary imaging modalities if needed (additional projections, ultrasound, CT, MRI). Suggest follow-up imaging timeframe if applicable. Recommend clinical correlation or additional diagnostics.]

**Referências:**
[Include only if citing specific criteria, classifications, or measurement standards used in the interpretation.]

CRITICAL FORMATTING RULES:
- Your response MUST start IMMEDIATELY with "**Descrição dos Achados:**"
- No preamble, greeting, or introduction
- Use professional veterinary medical terminology in Portuguese (Brazil)
- Be concise but thorough
- Maintain objectivity and acknowledge uncertainty when appropriate

PROFESSIONAL STANDARDS:
- Adopt the tone of a board-certified veterinary radiologist
- Balance detail with clinical relevance
- Prioritize patient safety by recommending additional studies when diagnosis is uncertain
- Consider the referring veterinarian's clinical question and provide actionable insights

"""
        _safe_print("Enviando imagens para análise da IA (isso pode levar alguns segundos)...")
        try:
            content: list = [prompt] + images
            response = self.model.generate_content(content)
            text = response.text.strip()

            pattern = r"\*\*Descri[çc][ãa]o dos Achados:?\*\*"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                text = text[match.start() :]
            else:
                simple = re.search(r"\*\*Descri[çc][ãa]o", text, re.IGNORECASE)
                if simple:
                    text = text[simple.start() :]

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
        """
        Gera novo laudo considerando correções do especialista e o laudo anterior.
        Usado no fluxo 'Gerar Laudo c/ Correções'.
        """
        especie = (paciente_info or {}).get("especie", "Não informado")
        raca = (paciente_info or {}).get("raca", "Não informado")
        idade = (paciente_info or {}).get("idade", "Não informado")
        sexo = (paciente_info or {}).get("sexo", "Não informado")
        historico = (paciente_info or {}).get("historico_clinico", "") or (
            paciente_info or {}).get("observacoes", "") or "Não informado"
        suspeita = (paciente_info or {}).get("suspeita_clinica", "Não informado")
        regiao = (paciente_info or {}).get("regiao_estudo", "Não informado")

        prompt = f"""You are a specialist veterinary radiologist. The specialist has reviewed a previous report and provided corrections. Generate a NEW corrected report in Portuguese (Brazil) that incorporates these corrections.

🚨 CORREÇÕES DO ESPECIALISTA:
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

Generate a complete new report that fixes the errors indicated by the specialist. Your response MUST start immediately with "**Descrição dos Achados:**". Use professional veterinary terminology in Portuguese (Brazil).
"""
        _safe_print("Gerando laudo com correções do especialista...")
        try:
            content: list = [prompt] + images
            response = self.model.generate_content(content)
            text = response.text.strip()
            pattern = r"\*\*Descri[çc][ãa]o dos Achados:?\*\*"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                text = text[match.start():]
            return re.sub(r"\n{3,}", "\n\n", text).strip() or text
        except Exception as e:
            return (
                "[ERRO NA IA: Não foi possível gerar o laudo. "
                f"Detalhe: {str(e)}]"
            )
