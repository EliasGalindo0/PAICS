"""
Dashboard do Usuário
"""
import streamlit as st
from datetime import datetime
from auth.auth_utils import get_current_user, clear_session
from database.connection import get_db
from database.models import Requisicao, Laudo, User
import os
import tempfile
from PIL import Image
import io

st.set_page_config(page_title="Dashboard Usuário - PAICS", page_icon="👤", layout="wide")

# Verificar autenticação
if not st.session_state.get('authenticated'):
    st.switch_page("pages/login.py")

if st.session_state.get('role') == 'admin':
    st.switch_page("pages/admin_dashboard.py")

# Inicializar componentes
db = get_db()
requisicao_model = Requisicao(db.requisicoes)
laudo_model = Laudo(db.laudos)
user_model = User(db.users)

# Sidebar
with st.sidebar:
    st.title("👤 Meu Dashboard")
    user = get_current_user()
    if user:
        st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
        st.write(f"**Email:** {user.get('email')}")

    st.divider()

    if st.button("🚪 Sair", use_container_width=True):
        clear_session()
        st.switch_page("pages/login.py")

    st.divider()

    # Navegação
    page = st.radio(
        "Navegação",
        ["Nova Requisição", "Meus Laudos"],
        key="user_nav"
    )

# Página principal
if page == "Nova Requisição":
    st.header("📤 Nova Requisição de Laudo")

    with st.form("nova_requisicao"):
        col1, col2 = st.columns(2)

        with col1:
            paciente = st.text_input("Nome do Paciente *")
            tutor = st.text_input("Nome do Tutor *")
            clinica = st.text_input("Nome da Clínica")

        with col2:
            tipo_exame = st.selectbox("Tipo de Exame *", ["raio-x", "ultrassom"])
            observacoes = st.text_area("Observações", height=100)

        st.subheader("📷 Imagens do Exame")
        uploaded_files = st.file_uploader(
            "Selecione as imagens (JPG, PNG, DICOM)",
            type=['jpg', 'jpeg', 'png', 'dcm', 'dicom', 'bmp', 'tiff'],
            accept_multiple_files=True
        )

        # Preview das imagens
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} arquivo(s) selecionado(s)**")
            cols = st.columns(min(3, len(uploaded_files)))
            for idx, file in enumerate(uploaded_files[:3]):
                with cols[idx]:
                    try:
                        img = Image.open(file)
                        st.image(img, caption=file.name, use_container_width=True)
                    except:
                        st.write(f"Arquivo: {file.name}")

        submit = st.form_submit_button("📤 Enviar Requisição", type="primary")

        if submit:
            if not paciente or not tutor:
                st.error("Por favor, preencha pelo menos o nome do paciente e do tutor")
            elif not uploaded_files:
                st.error("Por favor, selecione pelo menos uma imagem")
            else:
                # Salvar imagens temporariamente
                # Em produção, você salvaria em um storage adequado (S3, etc)
                user_id = st.session_state.get('user_id')
                imagens_paths = []

                # Criar diretório para imagens do usuário
                user_images_dir = os.path.join("uploads", user_id)
                os.makedirs(user_images_dir, exist_ok=True)

                for file in uploaded_files:
                    # Salvar arquivo
                    file_path = os.path.join(user_images_dir, file.name)
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                    imagens_paths.append(file_path)

                # Criar requisição
                try:
                    req_id = requisicao_model.create(
                        user_id=user_id,
                        imagens=imagens_paths,
                        paciente=paciente,
                        tutor=tutor,
                        clinica=clinica,
                        tipo_exame=tipo_exame,
                        observacoes=observacoes
                    )
                    st.success(f"✅ Requisição enviada com sucesso! ID: {req_id[:8]}")
                    st.info(
                        "Aguarde a análise do administrador. Você receberá uma notificação quando o laudo estiver pronto.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao criar requisição: {str(e)}")

elif page == "Meus Laudos":
    st.header("📋 Meus Laudos")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "pendente", "validado", "liberado", "rejeitado"]
        )
    with col2:
        search_paciente = st.text_input("🔍 Buscar por Paciente")
    with col3:
        search_tutor = st.text_input("🔍 Buscar por Tutor")

    # Buscar laudos
    user_id = st.session_state.get('user_id')
    status = None if status_filter == "Todos" else status_filter
    laudos = laudo_model.find_by_user(user_id, status=status)

    # Aplicar filtros de busca
    if search_paciente:
        search_lower = search_paciente.lower()
        laudos = [
            l for l in laudos
            if search_lower in l.get('metadata', {}).get('paciente', '').lower()
        ]

    if search_tutor:
        search_lower = search_tutor.lower()
        laudos = [
            l for l in laudos
            if search_lower in l.get('metadata', {}).get('tutor', '').lower()
        ]

    st.metric("Total de Laudos", len(laudos))

    # Lista de laudos
    if not laudos:
        st.info("Você ainda não possui laudos. Envie uma nova requisição para começar!")
    else:
        for laudo in laudos:
            # Buscar requisição associada
            req = requisicao_model.find_by_id(laudo.get('requisicao_id'))

            status_badge = {
                "pendente": "⏳ Pendente",
                "validado": "✅ Validado",
                "liberado": "📤 Liberado",
                "rejeitado": "❌ Rejeitado"
            }.get(laudo.get('status'), laudo.get('status'))

            with st.expander(f"📄 {req.get('paciente', 'Sem nome') if req else 'N/A'} - {status_badge}"):
                col1, col2 = st.columns(2)

                with col1:
                    if req:
                        st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                        st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                        st.write(f"**Clínica:** {req.get('clinica', 'N/A')}")
                        st.write(f"**Tipo de Exame:** {req.get('tipo_exame', 'N/A')}")

                with col2:
                    st.write(f"**Status:** {laudo.get('status', 'N/A')}")
                    st.write(f"**Criado em:** {laudo.get('created_at', 'N/A')}")
                    if laudo.get('liberado_at'):
                        st.write(f"**Liberado em:** {laudo.get('liberado_at')}")

                # Mostrar laudo se estiver liberado
                if laudo.get('status') == 'liberado':
                    st.divider()
                    st.subheader("📝 Laudo")
                    st.text_area(
                        "Conteúdo do Laudo",
                        value=laudo.get('texto', ''),
                        height=300,
                        disabled=True
                    )

                    # Botões de download
                    col_dl1, col_dl2 = st.columns(2)

                    with col_dl1:
                        # Aqui você implementaria a geração de Word
                        st.download_button(
                            "📥 Baixar como Word",
                            data="",  # Placeholder
                            file_name=f"laudo_{req.get('paciente', 'exame')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            disabled=True
                        )

                    with col_dl2:
                        # Aqui você implementaria a geração de PDF
                        st.download_button(
                            "📥 Baixar como PDF",
                            data="",  # Placeholder
                            file_name=f"laudo_{req.get('paciente', 'exame')}.pdf",
                            mime="application/pdf",
                            disabled=True
                        )
                elif laudo.get('status') == 'validado':
                    st.info("✅ Laudo validado! Aguardando liberação final.")
                elif laudo.get('status') == 'pendente':
                    st.info("⏳ Laudo em análise. Aguarde a validação do administrador.")
                else:
                    st.warning(f"Status: {laudo.get('status')}")
