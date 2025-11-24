"""
PAICS - Aplicação Streamlit para Análise de Imagens Veterinárias com IA
Interface web para upload de PDFs, geração de laudos e edição.
"""

import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
import io
import os
import tempfile
from dotenv import load_dotenv
from main import VetAIAnalyzer, VetReportGenerator
from fpdf import FPDF
from fpdf.enums import Align
import pytesseract
import re

# --- Carregar variáveis de ambiente do arquivo .env ---
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="PAICS - Análise de Imagens Veterinárias",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificar e configurar API Key
# A chave pode ser definida no arquivo .env ou como variável de
# ambiente do sistema
API_KEY = os.getenv("GOOGLE_API_KEY", "SUA_API_KEY_AQUI")
if "SUA_API_KEY_AQUI" not in API_KEY and API_KEY:
    genai.configure(api_key=API_KEY)

# Inicializar o gerador de relatórios


@st.cache_resource
def init_report_generator():
    """Inicializa o gerador de relatórios (cached para melhor performance)"""
    # Usar diretório temporário do Streamlit ou variável de ambiente
    temp_dir = os.getenv("STREAMLIT_TEMP_DIR", "temp_laudos")
    return VetReportGenerator(output_dir=temp_dir)

# Inicializar o analisador de IA


@st.cache_resource
def init_ai_analyzer():
    """Inicializa o analisador de IA (cached para melhor performance)"""
    if "SUA_API_KEY_AQUI" in API_KEY or not API_KEY:
        return None
    return VetAIAnalyzer()


def pdf_to_images(pdf_bytes):
    """Converte PDF em bytes para lista de imagens PIL"""
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_path = tmp_file.name

    try:
        # Abrir PDF e converter páginas em imagens
        doc = fitz.open(tmp_path)
        pil_images = []

        # Usar zoom configurável via variável de ambiente
        zoom = float(os.getenv("PDF_ZOOM_FACTOR", "2.0"))

        for page in doc:
            # Zoom configurável para garantir que a IA veja detalhes finos
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            pil_images.append(img)

        doc.close()
        return pil_images
    finally:
        # Limpar arquivo temporário
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def create_docx_from_edited(images, edited_text, paciente="", data=""):
    """Cria documento Word com laudo primeiro e depois as imagens"""
    doc = Document()

    # Estilos (configuráveis)
    style = doc.styles['Normal']
    style.font.name = os.getenv("DOC_FONT_NAME", "Calibri")
    font_size = int(os.getenv("DOC_FONT_SIZE", "11"))
    style.font.size = Pt(font_size)

    # Cabeçalho
    head = doc.add_heading('LAUDO VETERINÁRIO DE IMAGEM', 0)
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER

    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    paciente_text = (
        paciente if paciente else "____________________"
    )
    table.rows[0].cells[0].text = f"Paciente/Tutor: {paciente_text}"
    data_text = data if data else "____/____/______"
    table.rows[0].cells[1].text = f"Data: {data_text}"
    doc.add_paragraph()

    # NOVA ORDEM: Laudo primeiro
    doc.add_heading('Laudo', level=1)

    # Nota de aviso (se foi gerado por IA)
    if edited_text and st.session_state.get('original_laudo'):
        warning_text = (
            "Nota: Este laudo foi gerado automaticamente e revisado pelo "
            "Médico Veterinário."
        )
        warning = doc.add_paragraph(warning_text)
        warning.runs[0].font.color.rgb = RGBColor(255, 140, 0)  # Laranja
        warning.runs[0].font.italic = True
        doc.add_paragraph()

    # Inserir o texto editado
    # Substitui quebras de linha duplas por parágrafos separados
    paragraphs = edited_text.split('\n')
    for para in paragraphs:
        if para.strip():
            doc.add_paragraph(para.strip())

    # NOVA ORDEM: Imagens depois do laudo
    doc.add_page_break()
    doc.add_heading('Imagens do Exame', level=1)
    for i, img in enumerate(images):
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        image_width = float(os.getenv("IMAGE_WIDTH_INCHES", "5.5"))
        p.add_run().add_picture(img_byte_arr, width=Inches(image_width))
        doc.add_paragraph(f"Imagem {i + 1}").style = "Caption"

    # Rodapé de Assinatura apenas no final
    doc.add_paragraph()
    doc.add_paragraph("_" * 50)
    doc.add_paragraph("Assinatura e Carimbo do Veterinário Responsável")

    # Converter para bytes
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes.getvalue()


class PDF(FPDF):
    """Classe customizada para PDF. O rodapé é adicionado manualmente."""

    def header(self):
        pass

    def footer(self):
        pass


def create_pdf_from_edited(images, edited_text, paciente="", data=""):
    """Cria documento PDF com laudo primeiro, depois as imagens."""
    pdf = PDF('P', 'mm', 'A4')
    pdf.set_auto_page_break(auto=True, margin=15)

    # Usar Arial com codificação UTF-8 (suporte nativo do FPDF2)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Laudo', ln=1)
    pdf.ln(4)

    if paciente or data:
        pdf.set_font('Arial', '', 10)
        if paciente:
            pdf.cell(0, 6, f"Paciente/Tutor: {paciente}", ln=1)
        if data:
            pdf.cell(0, 6, f"Data: {data}", ln=1)
        pdf.ln(4)

    if edited_text and st.session_state.get('original_laudo'):
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(255, 140, 0)
        pdf.multi_cell(
            0, 5, "Nota: Este laudo foi gerado automaticamente e revisado pelo Médico Veterinário.")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    pdf.set_font('Arial', '', 11)
    # Limpar caracteres problemáticos e normalizar texto
    clean_text = edited_text.replace('**', '')
    # Substituir aspas curvas por aspas retas
    clean_text = clean_text.replace(''', "'").replace(''', "'")
    clean_text = clean_text.replace('"', '"').replace('"', '"')
    pdf.multi_cell(0, 5, clean_text)

    # NOVA ORDEM: Imagens depois do laudo
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Imagens do Exame', ln=1)
    pdf.ln(2)

    max_width_mm = 180

    for i, img in enumerate(images):
        w_px, h_px = img.size
        aspect_ratio = h_px / w_px
        img_width_mm = max_width_mm
        img_height_mm = img_width_mm * aspect_ratio

        if pdf.get_y() + img_height_mm > (297 - 30):
            pdf.add_page()

        try:
            pdf.image(img, w=img_width_mm, h=img_height_mm)
        except Exception:
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            pdf.image(buf, w=img_width_mm, h=img_height_mm)
            buf.close()

        pdf.set_font('Arial', 'I', 9)
        pdf.cell(0, 6, f"Imagem {i + 1}", ln=1, align=Align.C)
        pdf.ln(4)

    # Adicionar o rodapé de assinatura apenas na última página
    pdf.set_y(-30)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, "_" * 60, align=Align.L)
    pdf.ln(5)
    pdf.cell(0, 10, "Assinatura e Carimbo do Veterinário Responsável", align=Align.L)

    output = pdf.output(dest='S')
    if isinstance(output, bytearray):
        return bytes(output)
    if isinstance(output, bytes):
        return output
    if isinstance(output, str):
        return output.encode('latin-1', errors='replace')
    return bytes(output)


# configurar caminho do tesseract pelo env (opcional)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# idioma para o tesseract (por + eng por padrão; ajuste se desejar)
TESSERACT_LANG = os.getenv("TESSERACT_LANG", "por+eng")


def ocr_extract_metadata(images: list) -> tuple:
    """
    Roda OCR nas imagens e tenta extrair:
      - paciente/tutor (heurística: linhas que contenham 'Paciente', 'Nome', 'Tutor', 'Proprietário', 'Dono')
      - data (regex dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd e também busca por meses por extenso em pt)
    Retorna (paciente: str | '', data: str | '').
    """
    name_patterns = [
        r'(?i)Paciente[:\s]*([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-\.\s,]{3,60})',
        r'(?i)Nome[:\s]*([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-\.\s,]{3,60})',
        r'(?i)Tutor[:\s]*([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-\.\s,]{3,60})',
        r'(?i)Propriet[áa]rio[:\s]*([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-\.\s,]{3,60})',
        r'(?i)Dono[:\s]*([A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\-\.\s,]{3,60})'
    ]
    # date regex common forms
    date_regex = re.compile(r'(\d{2}[\/\-]\d{2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})')
    # month names (pt)
    month_names = r'(janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)'
    month_regex = re.compile(r'(\d{1,2}\s+' + month_names + r'\s+\d{4})', re.IGNORECASE)

    found_name = ""
    found_date = ""

    # Limitar número de páginas/processamento para economizar tempo
    for img in images:
        try:
            # opcional: melhorar contraste / conversão para grayscale
            gray = img.convert('L')
            # aumentar tamanho ajuda o OCR em alguns casos
            max_dim = 1600
            if max(gray.size) < max_dim:
                scale = max_dim / max(gray.size)
                new_size = (int(gray.width * scale), int(gray.height * scale))
                gray = gray.resize(new_size)

            text = pytesseract.image_to_string(gray, lang=TESSERACT_LANG)
            if not text or not text.strip():
                continue
            # procurar por data
            date_match = date_regex.search(text)
            if date_match and not found_date:
                found_date = date_match.group(1).strip()

            # procurar por mês por extenso
            month_match = month_regex.search(text)
            if month_match and not found_date:
                found_date = month_match.group(1).strip()

            # procurar por padrões de nome
            for pat in name_patterns:
                m = re.search(pat, text)
                if m:
                    candidate = m.group(1).strip()
                    # limpar ruídos
                    candidate = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ0-9\s\-,\.]', '', candidate)
                    if 3 <= len(candidate) <= 60:
                        found_name = candidate
                        break

            # se ainda não encontrou nome, tentar heurística: primeira linha com duas palavras (possivelmente nome)
            if not found_name:
                for line in text.splitlines():
                    line = line.strip()
                    if len(line) > 3 and ' ' in line and len(line) < 60:
                        # ignorar linhas com muitas dígitos (prováveis números)
                        if sum(c.isdigit() for c in line) < (len(line) * 0.4):
                            # escolher como candidato
                            found_name = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ0-9\s\-,\.]', '', line)
                            break

            # se já encontrou ambos, quebra
            if found_name and found_date:
                break
        except Exception:
            # não interromper o fluxo caso OCR falhe em uma imagem
            continue

    # normalizações simples
    if found_date:
        found_date = found_date.replace('\\', '/').strip()
    if found_name:
        # remover múltiplos espaços
        found_name = re.sub(r'\s{2,}', ' ', found_name).strip()

    return found_name, found_date


def is_template_page(img: Image.Image) -> bool:
    """Retorna True se a imagem parecer um formulário/template vazio."""
    try:
        gray = img.convert('L')
        max_dim = 800
        if max(gray.size) > max_dim:
            scale = max_dim / max(gray.size)
            new_size = (int(gray.width * scale), int(gray.height * scale))
            gray = gray.resize(new_size)

        text = pytesseract.image_to_string(gray, lang=TESSERACT_LANG)
        if not text:
            return False

        t = text.lower()

        # Verificar se tem cabeçalho de formulário E campos vazios (underscores)
        has_template_header = "laudo veterinário de imagem" in t or "laudo veterinario de imagem" in t
        has_form_fields = "paciente/tutor" in t or "paciente / tutor" in t
        has_empty_underscores = text.count("___") >= 3  # Pelo menos 3 campos vazios

        # É template apenas se tiver TODOS os critérios
        return has_template_header and has_form_fields and has_empty_underscores
    except Exception:
        return False


# Sidebar com configurações
with st.sidebar:
    st.title("⚙️ Configurações")

    # Verificação de API Key
    if "SUA_API_KEY_AQUI" in API_KEY or not API_KEY:
        st.error("⚠️ API Key não configurada!")
        st.info("Configure a variável de ambiente GOOGLE_API_KEY")
        st.code("export GOOGLE_API_KEY='sua_chave_aqui'")
        api_configured = False
    else:
        st.success("✅ API Key configurada")
        api_configured = True

    st.divider()

    st.subheader("ℹ️ Sobre")
    st.info(
        """
        **PAICS** - Sistema de Análise de Imagens Veterinárias com IA

        Faça upload de um PDF com imagens de raio-x ou ultrassom
        veterinário e receba um laudo técnico gerado por IA.

        O laudo gerado deve ser sempre revisado e validado por um Médico
        Veterinário qualificado.
        """
    )

# Título principal
st.title("🐾 PAICS - Análise de Imagens Veterinárias com IA")
st.markdown("Sistema automatizado para geração de laudos técnicos de imagens veterinárias")

# Inicializar variáveis de sessão
if 'pdf_uploaded' not in st.session_state:
    st.session_state.pdf_uploaded = False
if 'images' not in st.session_state:
    st.session_state.images = []
if 'images_for_report' not in st.session_state:  # NOVO
    st.session_state.images_for_report = []
if 'laudo_gerado' not in st.session_state:
    st.session_state.laudo_gerado = False
if 'laudo_text' not in st.session_state:
    st.session_state.laudo_text = ""
if 'original_laudo' not in st.session_state:
    st.session_state.original_laudo = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'ocr_paciente' not in st.session_state:
    st.session_state['ocr_paciente'] = ""
if 'ocr_data' not in st.session_state:
    st.session_state['ocr_data'] = ""
if 'ocr_raw' not in st.session_state:
    st.session_state['ocr_raw'] = ""
if 'ocr_done' not in st.session_state:
    st.session_state['ocr_done'] = False
if 'paciente_nome' not in st.session_state:
    st.session_state['paciente_nome'] = ""
if 'data_exame' not in st.session_state:
    st.session_state['data_exame'] = ""

# Upload de PDF
st.header("📤 Upload de PDF")

uploaded_file = st.file_uploader(
    "Selecione um arquivo PDF com imagens de exame veterinário",
    type=['pdf'],
    help="Faça upload de um PDF contendo imagens de raio-x ou ultrassom"
)

if uploaded_file is not None:
    # Processar PDF
    with st.spinner("Processando PDF..."):
        pdf_bytes = uploaded_file.read()
        all_images = pdf_to_images(pdf_bytes)
        total_pages = len(all_images)
        st.session_state.pdf_uploaded = True

        if total_pages == 0:
            st.warning("⚠️ Nenhuma página encontrada no PDF.")
            st.session_state.images = []
            st.session_state['id_page_image'] = None
        else:
            first_page = all_images[0]
            st.session_state['id_page_image'] = first_page

            if not st.session_state.get('ocr_done', False):
                with st.spinner("🔎 Extraindo informações (nome/data) via OCR..."):
                    try:
                        ocr_name, ocr_date = ocr_extract_metadata([first_page])

                        try:
                            raw_ocr = pytesseract.image_to_string(first_page, lang=TESSERACT_LANG)
                        except Exception:
                            raw_ocr = ""
                        st.session_state['ocr_raw'] = raw_ocr

                        if ocr_name:
                            st.session_state['ocr_paciente'] = ocr_name
                            st.session_state['paciente_nome'] = ocr_name
                        if ocr_date:
                            st.session_state['ocr_data'] = ocr_date
                            st.session_state['data_exame'] = ocr_date

                        st.session_state['ocr_done'] = True

                        if ocr_name or ocr_date:
                            st.success("✅ Informações sugeridas extraídas via OCR.")
                            st.rerun()
                    except Exception:
                        st.session_state['ocr_done'] = True
                        st.warning("OCR não conseguiu extrair informações automaticamente.")

            # CORREÇÃO: Enviar TODAS as imagens para análise da LLM
            # Mas armazenar separadamente as imagens para o laudo final (sem a primeira)
            st.session_state.images = all_images  # TODAS as páginas para LLM
            # Sem primeira página
            st.session_state.images_for_report = all_images[1:] if total_pages > 1 else []

            st.success(f"✅ PDF processado! {len(all_images)} página(s) para análise.")

    # Mostrar preview das imagens
    if st.session_state.get('id_page_image'):
        st.header("🧾 Página de Identificação")
        st.image(st.session_state['id_page_image'],
                 caption="Página 1: Dados do Paciente/Tutor (não incluída no laudo final)", use_container_width=True)

        if st.session_state.get('paciente_nome') or st.session_state.get('data_exame'):
            st.info(
                f"**Paciente/Tutor:** {st.session_state.get('paciente_nome', 'Não encontrado')} | **Data:** {st.session_state.get('data_exame', 'Não encontrada')}")

        if st.session_state.get('ocr_raw'):
            with st.expander("🔎 Texto extraído via OCR (debug)"):
                st.text_area("Texto OCR (bruto)", value=st.session_state.get(
                    'ocr_raw', ''), height=160)
        st.divider()

    if st.session_state.images:
        st.header("🖼️ Visualização de Todas as Imagens")
        st.info(f"📊 Total: {len(st.session_state.images)} página(s) serão analisadas pela IA")
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.images):
            with cols[i % 2]:
                st.image(img, caption=f"Página {i + 1}", use_container_width=True)
    else:
        st.warning("⚠️ Não há imagens de exame para análise após a filtragem.")

# CORREÇÃO: Mover para fora do bloco 'if uploaded_file is not None:'
if uploaded_file is None:
    st.info("👆 Faça upload de um arquivo PDF para começar")

# Seção de geração de laudo - agora fora do bloco de upload
if st.session_state.images and api_configured:
    st.header("🤖 Geração de Laudo com IA")

    col1, col2 = st.columns([1, 4])
    with col1:
        generate_button = st.button("🚀 Gerar Laudo", type="primary", use_container_width=True)

    if generate_button or st.session_state.laudo_gerado:
        if generate_button:
            # Limpar chat anterior ao gerar novo laudo
            st.session_state.chat_history = []
            # Gerar laudo
            with st.spinner("🤖 Analisando imagens com IA..."):
                try:
                    ai_analyzer = init_ai_analyzer()
                    if ai_analyzer:
                        laudo = ai_analyzer.generate_diagnosis(st.session_state.images)
                        st.session_state.laudo_text = laudo
                        st.session_state.original_laudo = laudo
                        st.session_state.laudo_gerado = True
                        st.rerun()
                    else:
                        st.error("Erro ao inicializar o analisador de IA")
                except Exception as e:
                    st.error(f"Erro ao gerar laudo: {str(e)}")
                    st.exception(e)

if st.session_state.laudo_gerado and st.session_state.laudo_text:
    st.header("📝 Laudo Gerado - Edite conforme necessário")

    # Editor de texto
    edited_laudo = st.text_area(
        "Laudo (edite o texto gerado pela IA)",
        value=st.session_state.laudo_text,
        height=400
    )

    # Atualizar laudo editado na sessão
    st.session_state.laudo_text = edited_laudo

    # Botões de ação
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 Salvar Edições", use_container_width=True):
            st.session_state.laudo_text = edited_laudo
            st.success("✅ Edições salvas!")

    with col2:
        # Botão para gerar novo laudo
        if st.button("🔄 Gerar Novo Laudo", use_container_width=True):
            st.session_state.laudo_gerado = False
            st.session_state.laudo_text = ""
            st.session_state.chat_history = []
            st.rerun()

    # Preparar nome do arquivo
    nome_arquivo = uploaded_file.name.replace('.pdf', '')
    paciente_nome_str = st.session_state.get('paciente_nome', "")
    if paciente_nome_str:
        nome_arquivo = f"{paciente_nome_str}_{nome_arquivo}"
    else:
        nome_arquivo = f"Laudo_{nome_arquivo}"

    # Gerar documento Word para download
    docx_bytes = create_docx_from_edited(
        st.session_state.images_for_report,  # MUDANÇA: usar images_for_report
        edited_laudo,
        paciente_nome_str,
        st.session_state.get('data_exame', "")
    )

    with col3:
        st.download_button(
            label="📥 Baixar como Word",
            data=docx_bytes,
            file_name=f"{nome_arquivo}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    with col4:
        try:
            pdf_bytes = create_pdf_from_edited(
                st.session_state.images_for_report,  # MUDANÇA: usar images_for_report
                edited_laudo,
                paciente_nome_str,
                st.session_state.get('data_exame', "")
            )
            st.download_button(
                label="📥 Baixar como PDF",
                data=pdf_bytes,
                file_name=f"{nome_arquivo}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
            st.exception(e)

    st.divider()

    # Chat com a IA sobre o laudo
    with st.expander("💬 **Converse com a IA para refinar o laudo**"):
        # Exibir histórico do chat
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Input do usuário
        if prompt := st.chat_input("Faça uma pergunta ou peça uma alteração..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Gerar resposta da IA
            with st.chat_message("assistant"):
                with st.spinner("Analisando seu pedido..."):
                    ai_analyzer = init_ai_analyzer()
                    if ai_analyzer:
                        # Montar o prompt de contexto para o chat
                        chat_prompt = f"""
                        Você é um assistente de radiologia veterinária.
                        O laudo atual é:
                        ---
                        {edited_laudo}
                        ---
                        Com base nas imagens já fornecidas e no laudo acima, responda ao seguinte pedido do usuário: "{prompt}"
                        Seja direto e profissional. Se o usuário pedir uma alteração, forneça o texto atualizado.
                        """
                        content_for_ai = [chat_prompt] + st.session_state.images
                        response = ai_analyzer.model.generate_content(content_for_ai)
                        response_text = response.text
                        st.markdown(response_text)
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": response_text})
                    else:
                        st.error("Analisador de IA não inicializado.")

    st.divider()

    # Preview do laudo formatado
    with st.expander("👁️ Visualizar Laudo Formatado"):
        st.markdown("### Laudo Veterinário")
        if paciente_nome_str:
            st.markdown(f"**Paciente/Tutor:** {paciente_nome_str}")
        if st.session_state.get('data_exame'):
            st.markdown(f"**Data:** {st.session_state.get('data_exame')}")
        st.markdown("---")
        # Converter quebras de linha para markdown
        laudo_display = edited_laudo.replace('\n', '  \n')
        st.markdown(laudo_display)

st.divider()
st.caption(
    "⚠️ **Importante:** Este sistema gera laudos sugeridos que devem ser "
    "sempre revisados e validados por um Médico Veterinário qualificado "
    "antes de serem utilizados. A IA serve como ferramenta de apoio, "
    "não substitui o julgamento clínico profissional."
)
