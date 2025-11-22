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
    """Cria documento Word com imagens e laudo editado"""
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

    # Seção de Imagens
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

    # Seção do Laudo
    doc.add_page_break()
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
    paragraphs = edited_text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            doc.add_paragraph(para.strip())

    # Rodapé de Assinatura
    doc.add_paragraph("_" * 50)
    doc.add_paragraph("Assinatura e Carimbo do Veterinário Responsável")

    # Converter para bytes
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes.getvalue()


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

    # Informações do paciente (opcional)
    st.subheader("📋 Informações do Paciente")
    paciente_nome = st.text_input("Nome do Paciente/Tutor", value="")
    data_exame = st.text_input("Data do Exame", value="")

    st.divider()

    # Sobre o app
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
st.markdown(
    "Sistema automatizado para geração de laudos técnicos de imagens veterinárias")

# Inicializar variáveis de sessão
if 'pdf_uploaded' not in st.session_state:
    st.session_state.pdf_uploaded = False
if 'images' not in st.session_state:
    st.session_state.images = []
if 'laudo_gerado' not in st.session_state:
    st.session_state.laudo_gerado = False
if 'laudo_text' not in st.session_state:
    st.session_state.laudo_text = ""
if 'original_laudo' not in st.session_state:
    st.session_state.original_laudo = ""

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
        images = pdf_to_images(pdf_bytes)
        st.session_state.images = images
        st.session_state.pdf_uploaded = True
        st.success(f"✅ PDF processado! {len(images)} página(s) encontrada(s).")

    # Mostrar preview das imagens
    if images:
        st.header("🖼️ Visualização das Imagens")
        num_cols = 2

        for i, img in enumerate(images):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.image(
                    img, caption=f"Imagem {i + 1}", use_container_width=True)
            with col2:
                st.metric("Dimensões", f"{img.width}x{img.height}")

        st.divider()

        # Botão para gerar laudo
        if api_configured:
            st.header("🤖 Geração de Laudo com IA")

            col1, col2 = st.columns([1, 4])
            with col1:
                generate_button = st.button(
                    "🚀 Gerar Laudo", type="primary", use_container_width=True)

            if generate_button or st.session_state.laudo_gerado:
                if generate_button:
                    # Gerar laudo
                    with st.spinner("🤖 Analisando imagens com IA (isso pode levar alguns segundos)..."):
                        try:
                            ai_analyzer = init_ai_analyzer()
                            if ai_analyzer:
                                laudo = ai_analyzer.generate_diagnosis(images)
                                st.session_state.laudo_text = laudo
                                st.session_state.original_laudo = laudo
                                st.session_state.laudo_gerado = True
                                st.rerun()
                            else:
                                st.error(
                                    "Erro ao inicializar o analisador de IA")
                        except Exception as e:
                            st.error(f"Erro ao gerar laudo: {str(e)}")
                            st.exception(e)

                # Mostrar e editar laudo
                if st.session_state.laudo_gerado and st.session_state.laudo_text:
                    st.header("📝 Laudo Gerado - Edite conforme necessário")

                    # Editor de texto
                    edited_laudo = st.text_area(
                        "Laudo (edite conforme necessário)",
                        value=st.session_state.laudo_text,
                        height=400,
                        help="Edite o laudo gerado pela IA conforme necessário"
                    )

                    # Atualizar laudo editado na sessão
                    st.session_state.laudo_text = edited_laudo

                    # Botões de ação
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("💾 Salvar Edições", use_container_width=True):
                            st.session_state.laudo_text = edited_laudo
                            st.success("✅ Edições salvas!")

                    with col2:
                        # Botão para gerar novo laudo
                        if st.button("🔄 Gerar Novo Laudo", use_container_width=True):
                            st.session_state.laudo_gerado = False
                            st.session_state.laudo_text = ""
                            st.rerun()

                    with col3:
                        # Gerar documento Word para download
                        docx_bytes = create_docx_from_edited(
                            st.session_state.images,
                            edited_laudo,
                            paciente_nome,
                            data_exame
                        )

                        nome_arquivo = uploaded_file.name.replace('.pdf', '')
                        if paciente_nome:
                            nome_arquivo = (
                                f"{paciente_nome}_{nome_arquivo}"
                            )
                        else:
                            nome_arquivo = f"Laudo_{nome_arquivo}"

                        mime_type = (
                            "application/vnd.openxmlformats-officedocument"
                            ".wordprocessingml.document"
                        )
                        st.download_button(
                            label="📥 Baixar Documento Word",
                            data=docx_bytes,
                            file_name=f"{nome_arquivo}.docx",
                            mime=mime_type,
                            use_container_width=True,
                            type="primary"
                        )

                    st.divider()

                    # Preview do laudo formatado
                    with st.expander("👁️ Visualizar Laudo Formatado"):
                        st.markdown("### Laudo Veterinário")
                        if paciente_nome:
                            st.markdown(f"**Paciente/Tutor:** {paciente_nome}")
                        if data_exame:
                            st.markdown(f"**Data:** {data_exame}")
                        st.markdown("---")
                        # Converter quebras de linha para markdown
                        laudo_display = edited_laudo.replace('\n', '  \n')
                        st.markdown(laudo_display)
        else:
            st.warning(
                "⚠️ Configure a API Key para gerar laudos automaticamente"
            )
            st.info(
                "Você ainda pode fazer upload e visualizar as imagens do PDF."
            )
else:
    st.info("👆 Faça upload de um arquivo PDF para começar")

# Rodapé
st.divider()
st.caption(
    "⚠️ **Importante:** Este sistema gera laudos sugeridos que devem ser "
    "sempre revisados e validados por um Médico Veterinário qualificado "
    "antes de serem utilizados. A IA serve como ferramenta de apoio, "
    "não substitui o julgamento clínico profissional."
)
