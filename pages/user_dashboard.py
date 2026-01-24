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
import io
from fpdf import FPDF
from fpdf.enums import XPos, YPos
# PIL.Image será importado lazy quando necessário (evita problemas com Python 3.13)

st.set_page_config(
    page_title="Dashboard Usuário - PAICS",
    page_icon="👤",
    layout="wide",
    menu_items=None
)

# Ocultar menu de navegação de páginas
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Verificar autenticação
if not st.session_state.get('authenticated'):
    st.switch_page("pages/login.py")

if st.session_state.get('role') == 'admin':
    st.switch_page("pages/admin_dashboard.py")

# Inicializar componentes (necessário para verificação de primeiro acesso)
db = get_db()
requisicao_model = Requisicao(db.requisicoes)
laudo_model = Laudo(db.laudos)
user_model = User(db.users)

# Verificar se é primeiro acesso (obrigar alteração de senha)
if st.session_state.get('requer_alteracao_senha') or st.session_state.get('primeiro_acesso'):
    user = get_current_user()
    if user and user.get('primeiro_acesso', False):
        st.title("🔐 Alteração de Senha Obrigatória")
        st.warning(
            "⚠️ Este é seu primeiro acesso. Você deve alterar sua senha temporária antes de continuar.")

        with st.form("alterar_senha_obrigatoria"):
            st.subheader("Alterar Senha")

            senha_atual = st.text_input("Senha Temporária Atual", type="password",
                                        help="Digite a senha temporária fornecida pelo administrador")
            nova_senha = st.text_input("Nova Senha", type="password",
                                       help="Mínimo de 6 caracteres")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")

            submit = st.form_submit_button(
                "✅ Alterar Senha", type="primary", use_container_width=True)

            if submit:
                from auth.auth_utils import verify_password, hash_password

                # Validar campos
                if not all([senha_atual, nova_senha, confirmar_senha]):
                    st.error("❌ Por favor, preencha todos os campos!")
                elif len(nova_senha) < 6:
                    st.error("❌ A nova senha deve ter no mínimo 6 caracteres!")
                elif nova_senha != confirmar_senha:
                    st.error("❌ As senhas não coincidem!")
                elif not verify_password(senha_atual, user['password_hash']):
                    st.error("❌ Senha temporária incorreta!")
                else:
                    # Atualizar senha e remover flag de primeiro acesso
                    nova_senha_hash = hash_password(nova_senha)
                    if user_model.update(user['id'], {
                        'password_hash': nova_senha_hash,
                        'primeiro_acesso': False,
                        'senha_temporaria': None
                    }):
                        st.success("✅ Senha alterada com sucesso! Redirecionando...")
                        st.session_state['requer_alteracao_senha'] = False
                        st.session_state['primeiro_acesso'] = False
                        st.rerun()
                    else:
                        st.error("❌ Erro ao alterar senha. Tente novamente.")

        st.stop()

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

    # Navegação (Meus Laudos como primeira aba ao abrir)
    page = st.radio(
        "Navegação",
        ["Meus Laudos", "Nova Requisição", "Minhas Faturas"],
        key="user_nav"
    )

# Página principal
if page == "Meus Laudos":
    st.header("📋 Meus Laudos")

    # Notificação de laudos recém liberados
    import datetime as _dt
    _now = _dt.datetime.utcnow()
    _last = st.session_state.get("last_meus_laudos_visit")
    st.session_state["last_meus_laudos_visit"] = _now
    _user_id = st.session_state.get("user_id")
    _liberados = laudo_model.find_by_user(_user_id, status="liberado") if _user_id else []
    _newly = []
    def _parse_dt(v):
        if v is None:
            return None
        if isinstance(v, _dt.datetime):
            return v.replace(tzinfo=None) if v.tzinfo else v
        try:
            t = _dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")[:26])
            return t.replace(tzinfo=None) if t.tzinfo else t
        except Exception:
            return None

    for _l in _liberados:
        _lib_at = _l.get("liberado_at")
        if _last is None:
            continue  # primeira visita: não notificar
        if not _lib_at:
            continue
        _t = _parse_dt(_lib_at)
        _last_naive = _parse_dt(_last)
        if _t is not None and _last_naive is not None and _t >= _last_naive:
            _newly.append(_l)
    if _newly and _last is not None:
        st.success(f"🎉 {len(_newly)} laudo(s) liberado(s)! Disponível(is) para download abaixo.")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        status = st.selectbox(
            "Filtrar por status",
            ["Todos", "Pendente", "Validado", "Concluído"],
            key="laudo_status_filter"
        )
    with col2:
        st.write("")
    with col3:
        st.write("")

    _uid = st.session_state.get("user_id")
    all_reqs = requisicao_model.find_by_user(_uid) if _uid else []
    reqs_dict = {r["id"]: r for r in all_reqs}

    status_map = {"Todos": None, "Pendente": "pendente", "Validado": "validado", "Concluído": "liberado"}
    status_val = status_map.get(status)
    laudos = laudo_model.find_by_user(st.session_state.get("user_id"), status=status_val)
    if status_val:
        laudos_filtrados = []
        for laudo in laudos:
            req = reqs_dict.get(laudo.get("requisicao_id"))
            if req:
                laudos_filtrados.append(laudo)
        laudos = laudos_filtrados
    else:
        laudos_filtrados = []
        for laudo in laudos:
            req = reqs_dict.get(laudo.get("requisicao_id"))
            if req:
                laudos_filtrados.append(laudo)
        laudos = laudos_filtrados

    st.metric("Total de Laudos", len(laudos))

    if not laudos:
        st.info("Você ainda não possui laudos. Envie uma nova requisição para começar!")
    else:
        for laudo in laudos:
            req = requisicao_model.find_by_id(laudo.get("requisicao_id"))
            if not req:
                continue
            status_badge = {"pendente": "⏳ Pendente", "validado": "✅ Validado", "liberado": "✅ Concluído"}.get(laudo.get("status"), laudo.get("status"))
            with st.expander(f"**{req.get('paciente', 'N/A')}** – {req.get('tutor', 'N/A')} – {status_badge}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                    st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                    st.write(f"**Tipo de Exame:** {req.get('tipo_exame', 'N/A')}")
                with col2:
                    st.write(f"**Status:** {status_badge}")
                    st.write(f"**Criado em:** {laudo.get('created_at', 'N/A')}")
                    if laudo.get('validado_at'):
                        st.write(f"**Validado em:** {laudo.get('validado_at')}")
                    if laudo.get('liberado_at'):
                        st.write(f"**Liberado em:** {laudo.get('liberado_at')}")

                if laudo.get("status") == "pendente":
                    st.divider()
                    st.subheader("📝 Laudo Pendente")
                    st.info("⏳ Este laudo está aguardando revisão e validação do administrador.")
                elif laudo.get("status") == "validado":
                    st.divider()
                    st.subheader("📝 Laudo Validado")
                    st.warning("✅ Este laudo foi validado e está aguardando liberação.")
                elif laudo.get("status") == "liberado":
                    st.divider()
                    st.subheader("📝 Laudo Liberado")
                    st.success("✅ Este laudo foi liberado e está disponível para download!")
                    st.text_area("Conteúdo do Laudo", value=laudo.get("texto", ""), height=300, disabled=True, key=f"liberado_{laudo['id']}")
                    try:
                        from ai.analyzer import load_images_for_analysis
                        imagens_paths = req.get("imagens", [])
                        images = load_images_for_analysis(imagens_paths)
                        pdf = FPDF("P", "mm", "A4")
                        pdf.set_auto_page_break(auto=True, margin=15)
                        def _clean(t):
                            for a, b in [("'", "'"), ("'", "'"), (""", '"'), (""", '"'), ("—", "-"), ("–", "-"), ("…", "..."), ("°", " graus")]:
                                t = t.replace(a, b)
                            t = t.replace("**", "")
                            try:
                                t.encode("latin-1")
                            except UnicodeEncodeError:
                                import unicodedata
                                t = unicodedata.normalize("NFKD", t).encode("latin-1", "ignore").decode("latin-1")
                            return t
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(0, 10, "LAUDO VETERINARIO DE IMAGEM", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                        pdf.ln(5)
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(0, 6, f"Paciente: {_clean(req.get('paciente', 'N/A'))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.cell(0, 6, f"Tutor: {_clean(req.get('tutor', 'N/A'))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(4)
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 10, "Laudo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(2)
                        pdf.set_font("Arial", "", 11)
                        pdf.multi_cell(0, 5, _clean(laudo.get("texto", "")))
                        if images:
                            pdf.add_page()
                            for i, img in enumerate(images):
                                w_px, h_px = img.size
                                ar = h_px / w_px
                                w_mm, h_mm = 180, 180 * ar
                                if pdf.get_y() + h_mm > 267:
                                    pdf.add_page()
                                buf = io.BytesIO()
                                img.save(buf, format="PNG")
                                buf.seek(0)
                                pdf.image(buf, w=w_mm, h=h_mm)
                                pdf.set_font("Arial", "I", 9)
                                pdf.cell(0, 6, f"Imagem {i+1}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                                pdf.ln(4)
                        pdf.set_y(-35)
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(0, 10, "_" * 60, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                        pdf.ln(2)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 5, "Dra. Laís Costa Muchiutti", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                        pdf.ln(2)
                        pdf.set_font("Arial", "", 9)
                        pdf.cell(0, 5, "Medica Veterinaria - CRMV-XX XXXXX", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        out = pdf.output(dest="S")
                        out = bytes(out) if isinstance(out, bytearray) else out
                        st.download_button("📥 Baixar como PDF", data=out, file_name=f"laudo_{req.get('paciente', 'exame').replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_{laudo['id']}")
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")
                        import traceback
                        traceback.print_exc()
                        st.download_button("📥 Baixar como PDF", data="", file_name="laudo.pdf", mime="application/pdf", disabled=True, use_container_width=True, key=f"dl_pdf_err_{laudo['id']}")

elif page == "Nova Requisição":
    st.header("📤 Nova Requisição de Laudo")

    # Mostrar feedback de requisição enviada
    if st.session_state.get('requisicao_enviada') and st.session_state.get('requisicao_info'):
        info = st.session_state['requisicao_info']
        st.success(f"✅ Requisição enviada com sucesso! ID: {info['req_id'][:8]}")

        st.info("📝 O veterinário administrador irá analisar e liberar o laudo. Você será notificado quando estiver disponível para download.")

        if st.button("✖️ Fechar", key="close_requisicao_feedback"):
            del st.session_state['requisicao_enviada']
            del st.session_state['requisicao_info']
            st.rerun()

        st.markdown("---")

    # Usar chave dinâmica para o formulário para garantir que os campos sejam limpos após submit
    form_key = f"nova_requisicao_{st.session_state.get('form_counter', 0)}"

    with st.form(form_key, clear_on_submit=True):
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

        # Preview das imagens (DICOM: salvar em temp e usar load_dicom_image)
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} arquivo(s) selecionado(s)**")
            cols = st.columns(min(3, len(uploaded_files)))
            for idx, file in enumerate(uploaded_files[:3]):
                with cols[idx]:
                    try:
                        ext = os.path.splitext(file.name)[1].lower()
                        if ext in (".dcm", ".dicom"):
                            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                                tmp.write(file.getbuffer().tobytes())
                                tmp_path = tmp.name
                            try:
                                from ai.analyzer import load_dicom_image
                                img = load_dicom_image(tmp_path)
                                if img is not None:
                                    st.image(img, caption=file.name, use_container_width=True)
                                else:
                                    st.write(f"Arquivo: {file.name} (DICOM)")
                            finally:
                                try:
                                    os.unlink(tmp_path)
                                except Exception:
                                    pass
                        else:
                            from PIL import Image
                            file.seek(0)
                            img = Image.open(file)
                            if img.mode != "RGB":
                                img = img.convert("RGB")
                            st.image(img, caption=file.name, use_container_width=True)
                    except Exception:
                        st.write(f"Arquivo: {file.name}")

        submit = st.form_submit_button("📤 Enviar Requisição", type="primary")

        if submit:
            if not paciente or not tutor:
                st.error("Por favor, preencha pelo menos o nome do paciente e do tutor")
            elif not uploaded_files:
                st.error("Por favor, selecione pelo menos uma imagem")
            else:
                # Salvar imagens (caminhos absolutos para IA e requisição)
                user_id = st.session_state.get('user_id')
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                uploads_base = os.path.join(project_root, "uploads")
                user_images_dir = os.path.join(uploads_base, user_id)
                os.makedirs(user_images_dir, exist_ok=True)
                imagens_paths = []

                for file in uploaded_files:
                    file_path = os.path.abspath(os.path.join(user_images_dir, file.name))
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                    imagens_paths.append(file_path)

                # Criar requisição e gerar laudo com IA em segundo plano (sem UI para o usuário)
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

                    laudo_id = None
                    try:
                        from dotenv import load_dotenv
                        _pr = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        load_dotenv(os.path.join(_pr, ".env"))
                        _api_key = os.getenv("GOOGLE_API_KEY", "SUA_API_KEY_AQUI")
                        if _api_key and _api_key != "SUA_API_KEY_AQUI":
                            from ai.analyzer import VetAIAnalyzer, load_images_for_analysis
                            images = load_images_for_analysis(imagens_paths)
                            if images:
                                ai_analyzer = VetAIAnalyzer()
                                texto_gerado = ai_analyzer.generate_diagnosis(images)
                                laudo_id = laudo_model.create(
                                    requisicao_id=req_id,
                                    texto=texto_gerado,
                                    texto_original=texto_gerado,
                                    status="pendente",
                                )
                    except Exception:
                        import traceback
                        traceback.print_exc()

                    st.session_state['requisicao_enviada'] = True
                    st.session_state['requisicao_info'] = {
                        'req_id': req_id,
                        'laudo_id': laudo_id,
                        'paciente': paciente
                    }
                    st.session_state['form_counter'] = st.session_state.get('form_counter', 0) + 1
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao criar requisição: {str(e)}")
                    import traceback
                    st.exception(e)

elif page == "Minhas Faturas":
    st.header("💰 Minhas Faturas")

    from database.models import Fatura
    fatura_model = Fatura(db.faturas)

    user_id = st.session_state.get('user_id')

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "pendente", "paga", "cancelada"]
        )
    with col2:
        periodo_search = st.text_input("🔍 Buscar por Período (opcional)")

    # Buscar faturas
    status = None if status_filter == "Todos" else status_filter
    faturas = fatura_model.find_by_user(user_id, status=status)

    # Filtrar por período se fornecido
    if periodo_search:
        faturas = [f for f in faturas if periodo_search.lower() in f.get('periodo', '').lower()]

    # Estatísticas
    total_pendente = sum(f.get('valor_total', 0) for f in faturas if f.get('status') == 'pendente')
    total_pago = sum(f.get('valor_total', 0) for f in faturas if f.get('status') == 'paga')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 Total de Faturas", len(faturas))
    with col2:
        st.metric("⏳ Pendentes", f"R$ {total_pendente:.2f}")
    with col3:
        st.metric("✅ Pagas", f"R$ {total_pago:.2f}")

    # Lista de faturas
    if not faturas:
        st.info("Você não possui faturas no momento.")
    else:
        for fatura in faturas:
            status_badge = {
                "pendente": "⏳ Pendente",
                "paga": "✅ Paga",
                "cancelada": "❌ Cancelada"
            }.get(fatura.get('status'), fatura.get('status'))

            with st.expander(f"💰 {fatura.get('periodo', 'N/A')} - R$ {fatura.get('valor_total', 0):.2f} - {status_badge}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Período:** {fatura.get('periodo', 'N/A')}")
                    st.write(f"**Valor Total:** R$ {fatura.get('valor_total', 0):.2f}")
                    st.write(f"**Status:** {status_badge}")
                    st.write(f"**Criada em:** {fatura.get('created_at', 'N/A')}")
                    if fatura.get('paga_at'):
                        st.write(f"**Paga em:** {fatura.get('paga_at')}")

                with col2:
                    st.write(f"**Quantidade de Exames:** {len(fatura.get('exames', []))}")

                    # Lista de exames
                    if fatura.get('exames'):
                        st.write("**Exames incluídos:**")
                        for idx, exame in enumerate(fatura.get('exames', [])[:10], 1):
                            req = requisicao_model.find_by_id(exame.get('requisicao_id', ''))
                            paciente = req.get('paciente', 'N/A') if req else 'N/A'
                            st.write(f"{idx}. {paciente} - R$ {exame.get('valor', 0):.2f}")
                        if len(fatura.get('exames', [])) > 10:
                            st.write(f"... e mais {len(fatura.get('exames', [])) - 10} exame(s)")

                if fatura.get('status') == 'pendente':
                    st.warning("⚠️ Esta fatura está pendente de pagamento.")
