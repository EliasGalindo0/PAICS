import fitz  # PyMuPDF
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
import io
import os
from dotenv import load_dotenv

# --- Carregar variáveis de ambiente do arquivo .env ---
load_dotenv()

# --- Configuração da IA ---
# A chave pode ser definida no arquivo .env ou como variável de
# ambiente do sistema
API_KEY = os.getenv("GOOGLE_API_KEY", "SUA_API_KEY_AQUI")
genai.configure(api_key=API_KEY)

# Configuração do Modelo (ajuste para 'gemini-2.5-pro' se disponível,
# usando 1.5 Pro como base atual)
# Pode ser configurado via variável de ambiente GEMINI_MODEL_NAME
MODEL_NAME = os.getenv(
    "GEMINI_MODEL_NAME", "gemini-2.5-pro"
)

# Configuração do diretório de saída (padrão: laudos_com_ia)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "laudos_com_ia")

# Configuração de processamento de PDF (zoom para melhor qualidade)
PDF_ZOOM_FACTOR = float(os.getenv("PDF_ZOOM_FACTOR", "2.0"))

# Configuração do tamanho da imagem no documento Word (em polegadas)
IMAGE_WIDTH_INCHES = float(os.getenv("IMAGE_WIDTH_INCHES", "5.5"))


class VetAIAnalyzer:
    """
    Classe responsável pela comunicação com a LLM (Gemini).
    """

    def __init__(self):
        self.model = genai.GenerativeModel(MODEL_NAME)

    def generate_diagnosis(self, images: list) -> str:
        """
        Envia imagens para o Gemini e retorna o laudo técnico.
        """
        # Prompt simplificado ao máximo
        prompt = """
        Analyze these veterinary images and write a technical report in Portuguese (Brazil).

        Start immediately with:
        **Descrição dos Achados:**
        [your detailed findings]

        **Impressão Diagnóstica:**
        [your diagnostic impression]

        **Conclusão:**
        [your conclusion]

        **Recomendações:**
        [your recommendations]

        **Referências:**
        [if applicable]

        CRITICAL: Your response MUST start with "**Descrição dos Achados:**" - nothing before it.
        """

        print(
            "🤖 Enviando imagens para análise da IA "
            "(isso pode levar alguns segundos)..."
        )
        try:
            content = [prompt] + images
            response = self.model.generate_content(content)
            text = response.text.strip()

            # ABORDAGEM FINAL: Usar regex para cortar TUDO antes de **Descrição
            import re

            # Buscar o padrão **Descrição (case insensitive)
            pattern = r'\*\*Descri[çc][ãa]o dos Achados:?\*\*'
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                # Cortar tudo antes do match
                start_pos = match.start()
                text = text[start_pos:]
            else:
                # Tentar padrão mais simples
                pattern_simple = r'\*\*Descri[çc][ãa]o'
                match_simple = re.search(pattern_simple, text, re.IGNORECASE)
                if match_simple:
                    start_pos = match_simple.start()
                    text = text[start_pos:]

            # Limpar linha por linha para remover porcarias
            lines = text.split('\n')
            cleaned = []

            for line in lines:
                stripped = line.strip()

                # Pular linhas vazias no início
                if not cleaned and not stripped:
                    continue

                # Pular separadores
                if stripped in ['---', '***', '___']:
                    continue

                # Pular headers markdown
                if stripped.startswith('#'):
                    continue

                # Pular tabelas
                if '|' in stripped:
                    continue

                # Pular linhas de metadata
                lower = stripped.lower()
                skip_patterns = [
                    'identificação',
                    'modalidade:',
                    'médico veterinário',
                    'data do exame:',
                    'dmv',
                    'especialista em'
                ]
                if any(p in lower for p in skip_patterns):
                    continue

                cleaned.append(line)

            result = '\n'.join(cleaned)

            # Remover múltiplas linhas vazias
            result = re.sub(r'\n{3,}', '\n\n', result)

            # Remover espaços no início/fim
            result = result.strip()

            return result if result else text

        except Exception as e:
            error_msg = (
                "[ERRO NA IA: Não foi possível gerar o laudo automático. "
                f"Detalhe: {str(e)}]"
            )
            return error_msg


class VetReportGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.ai_analyzer = VetAIAnalyzer()
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _pdf_to_pil_images(self, pdf_path: str) -> list:
        """Converte páginas do PDF em objetos PIL.Image para a IA e Word."""
        doc = fitz.open(pdf_path)
        pil_images = []

        for page in doc:
            # Zoom configurável para garantir que a IA veja detalhes finos
            zoom = PDF_ZOOM_FACTOR
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            pil_images.append(img)

        doc.close()
        return pil_images

    def create_report(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            print(f"Arquivo não encontrado: {pdf_path}")
            return

        # 1. Extração das Imagens
        print(f"📂 Processando arquivo: {pdf_path}")
        pil_images = self._pdf_to_pil_images(pdf_path)

        if not pil_images:
            print("Nenhuma imagem encontrada no PDF.")
            return

        # 2. Análise da IA (Gemini)
        ai_text_result = self.ai_analyzer.generate_diagnosis(pil_images)

        # 3. Geração do Documento Word
        self._build_docx(pdf_path, pil_images, ai_text_result)

    def _build_docx(self, original_path, images, ai_text):
        doc = Document()
        self._setup_styles(doc)

        # Cabeçalho
        self._create_header(doc)

        # Seção de Imagens
        doc.add_heading('Imagens do Exame', level=1)
        for i, img in enumerate(images):
            # Converter PIL para stream bytes para o python-docx
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(img_byte_arr, width=Inches(IMAGE_WIDTH_INCHES))
            doc.add_paragraph(f"Imagem {i + 1}").style = "Caption"

        # Seção do Laudo da IA
        doc.add_page_break()
        doc.add_heading('Laudo Sugerido (Gerado por IA)', level=1)

        # Nota de aviso
        warning_text = (
            "Nota: Este texto foi gerado automaticamente. "
            "O Médico Veterinário deve revisar e validar todas as "
            "informações."
        )
        warning = doc.add_paragraph(warning_text)
        warning.runs[0].font.color.rgb = RGBColor(255, 0, 0)
        warning.runs[0].font.italic = True

        # Inserir o texto da IA
        # O texto vem em Markdown, vamos apenas inseri-lo como texto
        # limpo por enquanto
        doc.add_paragraph(ai_text)

        # Rodapé de Assinatura
        doc.add_paragraph("_" * 30)
        doc.add_paragraph(
            "Assinatura e Carimbo do Veterinário Responsável"
        )

        # Salvar
        base_name = os.path.splitext(
            os.path.basename(original_path)
        )[0]
        filename = os.path.join(
            self.output_dir, f"Laudo_AI_{base_name}.docx"
        )
        doc.save(filename)
        print(f"✅ Laudo gerado com sucesso: {filename}")

    def _setup_styles(self, doc):
        style = doc.styles['Normal']
        style.font.name = 'Calibri'
        style.font.size = Pt(11)

    def _create_header(self, doc):
        head = doc.add_heading('LAUDO VETERINÁRIO DE IMAGEM', 0)
        head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        table = doc.add_table(rows=2, cols=2)
        table.style = 'Table Grid'
        table.rows[0].cells[0].text = "Paciente/Tutor: ____________________"
        table.rows[0].cells[1].text = "Data: ____/____/______"
        doc.add_paragraph()


# --- Execução ---
if __name__ == "__main__":
    # Exemplo: Coloque um PDF de raio-x na mesma pasta ou ajuste o caminho
    pdf_exame = "exame_raio_x.pdf"

    generator = VetReportGenerator()

    # Checagem de segurança para não quebrar se não tiver API key
    if "SUA_API_KEY_AQUI" in API_KEY:
        print("⚠️ AVISO: Você precisa configurar a GOOGLE_API_KEY no código ou nas variáveis de ambiente.")
    else:
        generator.create_report(pdf_exame)
