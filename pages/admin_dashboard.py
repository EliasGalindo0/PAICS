"""
Dashboard do Administrador
"""
from utils.theme import apply_custom_theme
from utils.observability import log
import time
from auth.auth_utils import verify_and_refresh_session
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from auth.auth_utils import get_current_user, clear_session, require_auth, logout_user
from database.connection import get_db
from database.models import Requisicao, Laudo, User, Fatura, Clinica, Veterinario
from utils.timezone import now, get_date_start, get_date_end, combine_date_local
import os
import io
import zipfile
import base64


def _ref_to_data_url_and_filename(ref: str) -> tuple[str | None, str]:
    """
    Carrega imagem por ref (GridFS id ou path) e retorna (data_url, filename).
    Evita st.image() que usa armazenamento efêmero em produção.
    """
    from database.image_storage import get_filename
    from ai.analyzer import load_images_for_analysis
    try:
        loaded = load_images_for_analysis([ref])
        if not loaded:
            return (None, get_filename(ref))
        buf = BytesIO()
        loaded[0].save(buf, format="PNG")
        buf.seek(0)
        data_url = f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"
        return (data_url, get_filename(ref))
    except Exception:
        return (None, get_filename(ref))

# IMPORTANTE: st.set_page_config deve vir PRIMEIRO
st.set_page_config(
    page_title="Dashboard Admin - PAICS",
    page_icon="👨‍⚕️",
    layout="wide",
    menu_items=None
)

# Aplicar tema customizado (deve ser chamado após st.set_page_config)
apply_custom_theme()

# Ocultar menu de navegação de páginas
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# Gate de autenticação (sem logs na UI)
# -----------------------------


def _load_tokens_from_query_params() -> bool:
    """Se auto_login estiver presente nos query params, decodifica tokens e coloca no session_state."""
    query_params = st.query_params
    if query_params.get('auto_login') != 'true':
        return False

    access_token_b64 = query_params.get('access_token', [''])[0]
    refresh_token_b64 = query_params.get('refresh_token', [''])[0]
    is_encoded = query_params.get('encoded') == 'true'

    if not access_token_b64 or not refresh_token_b64:
        return False

    if is_encoded:
        try:
            access_token = base64.b64decode(access_token_b64).decode()
            refresh_token = base64.b64decode(refresh_token_b64).decode()
        except Exception:
            access_token = access_token_b64
            refresh_token = refresh_token_b64
    else:
        access_token = access_token_b64
        refresh_token = refresh_token_b64

    st.session_state['access_token'] = access_token
    st.session_state['refresh_token'] = refresh_token
    st.query_params.clear()
    return True


def _ensure_authenticated_admin():
    # Se vier tokens via query params (auto_login), carregar
    _load_tokens_from_query_params()

    # Se temos tokens no session_state, validar/renovar
    if st.session_state.get('access_token') and st.session_state.get('refresh_token'):
        if not verify_and_refresh_session():
            st.switch_page("pages/login.py")
        if st.session_state.get('role') != 'admin':
            st.switch_page("pages/user_dashboard.py")
        return

    # Sem tokens: tentar restaurar do banco (fallback)
    from auth.auth_utils import try_restore_session_from_db
    if try_restore_session_from_db():
        st.rerun()

    st.switch_page("pages/login.py")


_ensure_authenticated_admin()

# Inicializar componentes (necessário para verificação de primeiro acesso)
db = get_db()
requisicao_model = Requisicao(db.requisicoes)
laudo_model = Laudo(db.laudos)
user_model = User(db.users)
fatura_model = Fatura(db.faturas)
clinica_model = Clinica(db.clinicas)
veterinario_model = Veterinario(db.veterinarios)
# VectorStore será importado lazy quando necessário (evita problemas com numpy/chromadb)


def _req_clinica_vet_display(req):
    """Resolve nome da clínica e do veterinário para uma requisição.
    Usa clinica_id/veterinario_id da req, depois texto da req, depois clínica do usuário da requisição."""
    user = user_model.find_by_id(req.get("user_id")) if req.get("user_id") else None
    clinica_nome = None
    if req.get("clinica_id"):
        c = clinica_model.find_by_id(req["clinica_id"])
        clinica_nome = (c or {}).get("nome") if c else None
    if not clinica_nome and (req.get("clinica") or "").strip():
        clinica_nome = req.get("clinica")
    if not clinica_nome and user and user.get("clinica_id"):
        c = clinica_model.find_by_id(user["clinica_id"])
        clinica_nome = (c or {}).get("nome") if c else None
    vet_nome = None
    if req.get("veterinario_id"):
        v = veterinario_model.find_by_id(req["veterinario_id"])
        vet_nome = (v or {}).get("nome") if v else None
    if not vet_nome and (req.get("medico_veterinario_solicitante") or "").strip():
        vet_nome = req.get("medico_veterinario_solicitante")
    if not vet_nome and user and user.get("clinica_id"):
        vets = veterinario_model.find_by_clinica(user["clinica_id"], apenas_ativos=True)
        vet_nome = (vets[0].get("nome") if vets else None) or ""
    return (clinica_nome or "—", vet_nome or "—")


def _formatar_texto_laudo_para_edicao(texto: str) -> str:
    """Normaliza o texto do laudo para exibição na caixa de edição.
    Converte sequências escapadas (\\n, \\t) em quebras/tabs reais e remove markdown
    (** negrito, *** separadores) para exibir texto limpo."""
    if not texto or not isinstance(texto, str):
        return ""
    t = texto
    t = t.replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n").replace("\\t", "\t")
    # Remover markdown de negrito (**texto**) e separadores (***, ---, ___)
    import re
    t = re.sub(r"\*\*\*+", "", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"___+", "", t)
    t = re.sub(r"---+", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


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
                    with st.spinner("🔐 Alterando senha..."):
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
    # Botão de alternar tema
    from utils.theme import theme_toggle_button
    theme_toggle_button()
    st.divider()

    st.title("👨‍⚕️ Admin Dashboard")
    user = get_current_user()
    if user:
        st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
        st.write(f"**E-mail:** {user.get('email')}")

    st.divider()

    if st.button("🚪 Sair", use_container_width=True, type="primary"):
        # Fazer logout primeiro
        logout_user(logout_all_devices=False)

        # Limpar todos os tokens do session_state também
        if 'access_token' in st.session_state:
            del st.session_state['access_token']
        if 'refresh_token' in st.session_state:
            del st.session_state['refresh_token']
        if 'remember_me' in st.session_state:
            del st.session_state['remember_me']

        # Limpar localStorage e redirecionar imediatamente via JavaScript
        st.markdown("""
            <script>
            (function() {
                // Limpar localStorage
                localStorage.removeItem('paics_user_id');
                localStorage.removeItem('paics_access_token');
                localStorage.removeItem('paics_refresh_token');
                
                // Forçar redirecionamento imediato
                setTimeout(function() {
                    window.location.href = '/login';
                }, 100);
            })();
            </script>
        """, unsafe_allow_html=True)

        # Também fazer switch_page como fallback
        st.switch_page("pages/login.py")
        st.stop()

    st.divider()

    # Navegação
    page = st.radio(
        "Navegação",
        ["Exames", "Nova Requisição", "Clínicas e Usuários",
            "Financeiro", "Knowledge Base e Aprendizado"],
        key="admin_nav"
    )

# Página principal baseada na seleção
if page == "Exames":
    st.header("📋 Exames")

    # Filtros e Data
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        # Filtro de data - key para manter valor após rerun (ex.: após geração em massa)
        filter_date = st.date_input("📅 Data", value=now().date(), key="req_filter_date")
        show_all_dates = st.checkbox("Mostrar todas as datas",
                                     value=False, key="req_show_all_dates")

        if show_all_dates:
            start_dt = None
            end_dt = None
        else:
            # Usar timezone local para os filtros
            start_dt = get_date_start(combine_date_local(filter_date))
            end_dt = get_date_end(combine_date_local(filter_date))

    with col_f2:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "pendente", "em_analise", "validado", "liberado", "rejeitado"]
        )
    with col_f3:
        tipo_filter = st.selectbox(
            "Filtrar por Tipo",
            ["Todos", "raio-x", "ultrassom"]
        )
    with col_f4:
        search_term = st.text_input(
            "🔍 Buscar (qualquer campo)",
            placeholder="Paciente, tutor, clínica, espécie, histórico..."
        )

    # Ordenação e visualização
    col_ord1, col_ord2, col_ord3 = st.columns(3)
    with col_ord1:
        sort_by = st.selectbox(
            "Ordenar por",
            ["Data (mais recente)", "Data (mais antigo)", "Status", "Clínica", "Paciente"],
            key="req_sort_by"
        )
    with col_ord2:
        view_mode = st.radio("Visualização", ["Rápida", "Detalhada"],
                             horizontal=True, key="req_view_mode")
    with col_ord3:
        st.write("")

    # Buscar todas as requisições do período para as estatísticas
    exames_periodo = requisicao_model.find_all(start_date=start_dt, end_date=end_dt)

    # Estatísticas rápidas baseadas no período filtrado
    pendentes_exames = [e for e in exames_periodo if e.get('status') == 'pendente']
    em_analise = [e for e in exames_periodo if e.get('status') == 'em_analise']
    liberadas_exames = [e for e in exames_periodo if e.get('status') == 'liberado']

    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric("📋 Total no Período", len(exames_periodo))
    with col_stat2:
        st.metric("⏳ Pendentes", len(pendentes_exames), delta=len(pendentes_exames)
                  if not show_all_dates else None, delta_color="off")
    with col_stat3:
        st.metric("🔍 Em Análise", len(em_analise))
    with col_stat4:
        st.metric("✅ Liberadas", len(liberadas_exames))

    st.divider()

    # Buscar requisições com filtro de status e data
    status = None if status_filter == "Todos" else status_filter
    exames = requisicao_model.find_all(status=status, start_date=start_dt, end_date=end_dt)

    # Aplicar filtros adicionais
    if tipo_filter != "Todos":
        exames = [e for e in exames if e.get('tipo_exame') == tipo_filter]

    if search_term:
        search_lower = search_term.lower().strip()

        def _searchable(r):
            parts = [
                e.get("paciente", ""), e.get("tutor", ""), e.get("clinica", ""),
                e.get("especie", ""), e.get("raca", ""), e.get(
                    "medico_veterinario_solicitante", ""),
                e.get("regiao_estudo", ""), e.get("suspeita_clinica", ""),
                e.get("historico_clinico", "") or e.get("observacoes", ""),
            ]
            return " ".join(p or "" for p in parts).lower()
        exames = [e for e in exames if search_lower in _searchable(e)]

    # Ordenação
    _status_order = {"pendente": 0, "em_analise": 1, "validado": 2, "liberado": 3, "rejeitado": 4}

    def _sort_key(e):
        dt = e.get("created_at") or datetime.min
        if "Status" in sort_by:
            return (_status_order.get(e.get("status"), 99), dt)
        if "Clínica" in sort_by:
            return (e.get("clinica", "").lower(), dt)
        if "Paciente" in sort_by:
            return (e.get("paciente", "").lower(), dt)
        return (dt,)

    reverse = "mais recente" in sort_by
    exames = sorted(exames, key=_sort_key, reverse=reverse)

    st.metric("Total de Exames", len(exames))

    # Mensagem de sucesso após geração em massa (persiste após rerun)
    bulk_msg = st.session_state.pop("bulk_gen_success", None)
    if bulk_msg:
        ok, err = bulk_msg.get("ok", 0), bulk_msg.get("err", 0)
        st.success(f"✅ Geração em massa concluída: {ok} laudo(s) gerado(s)." + (
            f" {err} erro(s)." if err else "") + " A lista abaixo foi atualizada.")

    # Requisições sem laudo (elegíveis para geração em massa)
    reqs_sem_laudo = [e for e in exames if not laudo_model.find_by_requisicao(e["id"]) and (e.get("imagens") or [])]
    n_sem_laudo = len(reqs_sem_laudo)
    if n_sem_laudo > 0:
        if st.button(f"🤖 Gerar laudos em massa ({n_sem_laudo} pendente(s))", type="primary", key="bulk_gen_btn", use_container_width=False):
            from ai.analyzer import load_images_for_analysis
            from ai.learning_system import LearningSystem
            progress_bar = st.progress(0.0, text="Iniciando geração em massa...")
            status_placeholder = st.empty()
            ok = 0
            err = 0
            for i, r in enumerate(reqs_sem_laudo):
                progress_bar.progress(
                    (i + 1) / len(reqs_sem_laudo), text=f"Gerando laudo {i + 1}/{len(reqs_sem_laudo)}: {(r.get('paciente') or 'N/A')[:30]}...")
                status_placeholder.caption(
                    f"Processando requisição #{r['id'][:8]} · Paciente: {(r.get('paciente') or 'N/A').upper()}")
                try:
                    selected_paths = r.get("imagens") or []
                    images = load_images_for_analysis(selected_paths)
                    if images:
                        ls = LearningSystem()
                        _obs_bulk = "\n".join(
                            o.get("texto", "").strip()
                            for o in (r.get("observacoes_usuario") or [])
                            if o.get("texto", "").strip()
                        )
                        paciente_info = {
                            "especie": r.get("especie", ""),
                            "raca": r.get("raca", ""),
                            "idade": r.get("idade", ""),
                            "sexo": r.get("sexo", ""),
                            "historico_clinico": (r.get("historico_clinico") or r.get("observacoes", "")),
                            "suspeita_clinica": r.get("suspeita_clinica", ""),
                            "regiao_estudo": r.get("regiao_estudo", ""),
                            "observacoes_adicionais_usuario": _obs_bulk,
                        }
                        texto_gerado, metadata = ls.generate_laudo(images, paciente_info, r["id"])
                        modelo_info = metadata.get("modelo_usado", "api_externa")
                        laudo_model.create(
                            requisicao_id=r["id"],
                            texto=texto_gerado,
                            texto_original=texto_gerado,
                            status="pendente",
                            modelo_usado=modelo_info,
                            usado_api_externa=metadata.get("usado_api_externa", True),
                            similaridade_casos=metadata.get("similaridade_casos"),
                            imagens_usadas=selected_paths,
                        )
                        ok += 1
                    else:
                        laudo_model.create(
                            requisicao_id=r["id"], texto="", texto_original="", status="pendente", imagens_usadas=selected_paths)
                        ok += 1
                except Exception as e:
                    err += 1
                    try:
                        laudo_model.create(
                            requisicao_id=r["id"], texto="", texto_original="", status="pendente")
                    except Exception:
                        pass
            progress_bar.progress(1.0, text="Concluído.")
            status_placeholder.empty()
            st.session_state["bulk_gen_success"] = {"ok": ok, "err": err}
            st.rerun()

    def _fmt_dt(x):
        """Formata datetime assumindo que valores sem tz são UTC e converte para GMT-3."""
        from datetime import timezone as _tzmod
        from utils.timezone import utc_to_local
        if x is None:
            return "—"
        if isinstance(x, datetime):
            # Se não tiver tz, assumir UTC (comportamento do MongoDB para datetimes)
            if x.tzinfo is None:
                x = x.replace(tzinfo=_tzmod.utc)
            # Converter para horário local (GMT-3)
            x_local = utc_to_local(x)
            return x_local.strftime("%d/%m/%Y %H:%M")
        return str(x)[:16]

    # Lista de requisições (todas no período/filtro; role para ver todas)
    if exames:
        st.caption(
            f"Mostrando **{len(exames)}** exame(s). Role a página para ver todas e clique para expandir cada uma.")
    for req in exames:
        status_req = req.get("status", "N/A")
        status_label = {"pendente": "⏳ Pendente", "em_analise": "🔍 Em análise", "validado": "✅ Validado",
                        "liberado": "✅ Concluída", "rejeitado": "❌ Rejeitada"}.get(status_req, status_req)
        n_imgs = len(req.get("imagens") or [])

        with st.expander(f"📄 #{req['id'][:8]} · {(req.get('paciente') or 'Sem nome').upper()} · {status_label} · {n_imgs} IMAGEM(NS)"):
            laudo = laudo_model.find_by_requisicao(req["id"])
            user = user_model.find_by_id(req.get("user_id")) if req.get("user_id") else None

            if view_mode == "Rápida":
                _clinica_rap, _ = _req_clinica_vet_display(req)
                clinica_rap = (_clinica_rap or "—").upper()
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Paciente:** {(req.get('paciente') or '—').upper()}")
                    st.write(f"**Tutor:** {(req.get('tutor') or '—').upper()}")
                    st.write(f"**Clínica:** {clinica_rap}")
                with c2:
                    st.write(f"**Status:** {(status_label or '—').upper()}")
                    st.write(f"**Data:** {_fmt_dt(req.get('created_at') or req.get('data_exame'))}")
                    st.write(f"**Tipo:** {(req.get('tipo_exame') or '—').upper()}")
                    st.write(f"**Imagens:** {n_imgs} ARQUIVO(S)")
                with c3:
                    if user:
                        st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
                    if laudo:
                        st.info(f"📝 Laudo: {laudo.get('status', 'N/A')}")
                    else:
                        st.warning("⏳ Laudo não criado")
                    _n_obs = len(req.get("observacoes_usuario") or [])
                    if _n_obs:
                        st.caption(f"📌 {_n_obs} observação(ões) do usuário")
                # Galeria rápida (expander)
                if n_imgs:
                    with st.expander("🖼️ Ver imagens", expanded=False):
                        imagens_paths = req.get("imagens") or []
                        n_cols_img = 5
                        for start in range(0, len(imagens_paths), n_cols_img):
                            cols = st.columns(n_cols_img)
                            for k, ref in enumerate(imagens_paths[start : start + n_cols_img]):
                                if k < len(cols):
                                    with cols[k]:
                                        data_url, nome = _ref_to_data_url_and_filename(ref)
                                        if data_url:
                                            nome_disp = nome[:40] + ("..." if len(nome) > 40 else "")
                                            st.markdown(
                                                f'<img src="{data_url}" style="width:100%;max-height:200px;object-fit:contain;border-radius:4px;">'
                                                f'<div style="text-align:center;font-size:0.8rem;color:#666;">{nome_disp}</div>',
                                                unsafe_allow_html=True,
                                            )
                                        else:
                                            st.caption(nome or str(ref)[:20])
            else:
                st.subheader("📋 Dados completos da requisição")
                # Resolver nome da clínica e do veterinário (req ou usuário da requisição)
                clinica_display, vet_display = _req_clinica_vet_display(req)
                clinica_display = (clinica_display or "—").upper()
                vet_display = (vet_display or "—").upper()
                def _up(s): return (s or "—").upper() if isinstance(
                    s, str) else (str(s).upper() if s is not None else "—")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**Paciente:**", _up(req.get("paciente")))
                    st.write("**Espécie:**", _up(req.get("especie")))
                    st.write("**Idade:**", _up(req.get("idade")))
                    st.write("**Raça:**", _up(req.get("raca")))
                    st.write("**Sexo:**", _up(req.get("sexo")))
                    st.write("**Tutor(a):**", _up(req.get("tutor")))
                    st.write("**Clínica solicitante:**", clinica_display)
                    st.write("**Médico(a) veterinário(a):**", vet_display)
                with col_b:
                    st.write("**Região de estudo:**", _up(req.get("regiao_estudo")))
                    st.write("**Suspeita clínica:**", _up(req.get("suspeita_clinica")))
                    st.write("**Plantão:**", _up(req.get("plantao")))
                    st.write("**Data da requisição:**",
                             _fmt_dt(req.get("created_at") or req.get("data_exame")))
                    st.write("**Status:**", (status_label or "—").upper())
                    st.write("**Tipo de exame:**", _up(req.get("tipo_exame")))
                    if user:
                        st.write("**Usuário:**", user.get("nome", user.get("username")),
                                 "·", user.get("email", ""))
                st.write("**Histórico clínico:**")
                hc = (req.get("historico_clinico") or req.get("observacoes") or "—").upper()
                st.text_area("", value=hc, height=80, disabled=True, key=f"hist_{req['id']}")

            # Observações adicionais enviadas pelo usuário (ele não edita a req, só adiciona notas)
            _obs_admin = req.get("observacoes_usuario") or []
            if _obs_admin:
                with st.expander("📌 Observações do usuário", expanded=True):
                    st.caption(
                        "O usuário enviou estas observações para considerar no laudo (sem alterar os dados originais da requisição).")
                    for _io, _ob in enumerate(reversed(_obs_admin)):
                        _txt = _ob.get("texto", "")
                        _dt = _ob.get("created_at", "")
                        if _dt and hasattr(_dt, "strftime"):
                            _dt = _dt.strftime("%d/%m/%Y %H:%M")
                        st.text_area("", value=_txt, height=70, disabled=True,
                                     key=f"adm_obs_{req['id']}_{_io}")
                        st.caption(f"Enviado em {_dt}")

            # Conteúdo do laudo: visível assim que o laudo existe (gerado em massa ou individualmente),
            # para não confundir o usuário que pensaria que precisa clicar em "Gerar" para ver o laudo já gerado.
            if laudo and (laudo.get("texto") or "").strip():
                texto_preview = _formatar_texto_laudo_para_edicao(laudo.get("texto", ""))
                with st.expander("📝 Conteúdo do laudo", expanded=True):
                    st.text_area(
                        "Conteúdo do laudo (somente leitura)",
                        value=texto_preview,
                        height=280,
                        disabled=False,
                        key=f"preview_laudo_{req['id']}",
                        label_visibility="collapsed",
                    )
                st.caption(
                    "Para editar o texto, liberar ou regenerar com correções, use **Editar Laudo** abaixo.")

            # Histórico de edições (auditoria: quem alterou o quê e quando)
            _hist = req.get("historico_edicoes") or []
            if _hist:
                with st.expander("📜 Histórico de edições da requisição", expanded=False):
                    st.caption(
                        "Registro de alterações feitas pelo admin. O usuário não pode editar a requisição.")
                    for _h in reversed(_hist):
                        _alt = _h.get("alteracoes", {})
                        _dt = _h.get("created_at", "")
                        if _dt and hasattr(_dt, "strftime"):
                            _dt = _dt.strftime("%d/%m/%Y %H:%M")
                        st.write(f"**{_dt}** (admin)")
                        for _campo, _val in _alt.items():
                            st.write(
                                f"- **{_campo}:** de «{_val.get('de', '')}» → «{_val.get('para', '')}»")
                        st.divider()

            # Editar informações da requisição (corrigir dados enviados pelo usuário) — registra no histórico
            with st.expander("✏️ Editar informações da requisição", expanded=False):
                with st.form(f"form_edit_req_{req['id']}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        epaciente = st.text_input("Paciente", value=req.get(
                            "paciente") or "", key=f"req_edit_pac_{req['id']}")
                        etutor = st.text_input("Tutor(a)", value=req.get(
                            "tutor") or "", key=f"req_edit_tutor_{req['id']}")
                        eespecie = st.text_input("Espécie", value=req.get(
                            "especie") or "", key=f"req_edit_esp_{req['id']}")
                        eidade = st.text_input("Idade", value=req.get(
                            "idade") or "", key=f"req_edit_idade_{req['id']}")
                        eraca = st.text_input("Raça", value=req.get(
                            "raca") or "", key=f"req_edit_raca_{req['id']}")
                        esexo = st.text_input("Sexo", value=req.get(
                            "sexo") or "", key=f"req_edit_sexo_{req['id']}")
                        eclinica_txt = st.text_input("Clínica (texto)", value=req.get(
                            "clinica") or "", key=f"req_edit_clinica_{req['id']}", help="Texto da clínica; se a requisição tiver vínculo por ID, este campo é complementar.")
                        evet_txt = st.text_input("Médico(a) veterinário(a) (texto)", value=req.get(
                            "medico_veterinario_solicitante") or "", key=f"req_edit_vet_{req['id']}")
                    with e2:
                        eregiao = st.text_input("Região de estudo", value=req.get(
                            "regiao_estudo") or "", key=f"req_edit_regiao_{req['id']}")
                        esuspeita = st.text_input("Suspeita clínica", value=req.get(
                            "suspeita_clinica") or "", key=f"req_edit_suspeita_{req['id']}")
                        eplantao = st.text_input("Plantão", value=req.get(
                            "plantao") or "", key=f"req_edit_plantao_{req['id']}")
                        etipo = st.selectbox("Tipo de exame", ["raio-x", "ultrassom"], index=0 if (
                            req.get("tipo_exame") or "raio-x") == "raio-x" else 1, key=f"req_edit_tipo_{req['id']}")
                        ehistorico = st.text_area("Histórico clínico", value=(req.get("historico_clinico") or req.get(
                            "observacoes") or ""), height=80, key=f"req_edit_hist_{req['id']}")
                    if st.form_submit_button("💾 Salvar alterações na requisição"):
                        updates = {
                            "paciente": epaciente.strip(),
                            "tutor": etutor.strip(),
                            "especie": eespecie.strip(),
                            "idade": eidade.strip(),
                            "raca": eraca.strip(),
                            "sexo": esexo.strip(),
                            "clinica": eclinica_txt.strip(),
                            "medico_veterinario_solicitante": evet_txt.strip(),
                            "regiao_estudo": eregiao.strip(),
                            "suspeita_clinica": esuspeita.strip(),
                            "plantao": eplantao.strip(),
                            "tipo_exame": etipo,
                            "historico_clinico": ehistorico.strip(),
                        }
                        current_user = get_current_user()
                        admin_id = (current_user or {}).get("id") or ""
                        if requisicao_model.update_with_history(req["id"], updates, admin_id):
                            st.success("Requisição atualizada. Alteração registrada no histórico.")
                            st.rerun()
                        else:
                            st.warning("Nenhuma alteração aplicada.")

            # Controle de edição inline
            editing_key = f"editing_{req['id']}"
            is_editing = st.session_state.get(editing_key, False)

            # Seleção de imagens para laudo (quando ainda não há laudo)
            imagens_paths = req.get("imagens") or []
            sel_key = f"img_sel_{req['id']}"
            if not laudo and imagens_paths:
                if sel_key not in st.session_state:
                    st.session_state[sel_key] = [True] * len(imagens_paths)
                # Comandos "Selecionar/Desselecionar Todas": aplicar antes de criar os checkboxes (evita modificar keys dos widgets após criação)
                cmd_all = st.session_state.pop(f"_cmd_sel_all_{req['id']}", False)
                cmd_none = st.session_state.pop(f"_cmd_sel_none_{req['id']}", False)
                if cmd_all or cmd_none:
                    st.session_state[sel_key] = [True] * \
                        len(imagens_paths) if cmd_all else [False] * len(imagens_paths)
                    for i in range(len(imagens_paths)):
                        st.session_state.pop(f"{sel_key}_{i}", None)
                    st.rerun()
                st.divider()
                with st.expander("🖼️ Imagens para o laudo (desmarque as que NÃO devem ir para a IA)", expanded=True):
                    n_cols = 5
                    for start in range(0, len(imagens_paths), n_cols):
                        row = st.columns(n_cols)
                        for k, idx in enumerate(range(start, min(start + n_cols, len(imagens_paths)))):
                            path = imagens_paths[idx]
                            with row[k]:
                                nome = os.path.basename(path)
                                st.checkbox(
                                    nome[:40] + ("..." if len(nome) > 40 else ""),
                                    value=st.session_state[sel_key][idx],
                                    key=f"{sel_key}_{idx}",
                                )
                                data_url, _ = _ref_to_data_url_and_filename(path)
                                if data_url:
                                    st.markdown(
                                        f'<img src="{data_url}" style="width:100%;max-height:180px;object-fit:contain;border-radius:4px;">',
                                        unsafe_allow_html=True,
                                    )
                    # Sincronizar lista com valores atuais dos checkboxes
                    st.session_state[sel_key] = [st.session_state.get(
                        f"{sel_key}_{i}", True) for i in range(len(imagens_paths))]
                    n_sel = sum(st.session_state[sel_key])
                    st.caption(
                        f"**{n_sel} de {len(imagens_paths)}** IMAGEM(NS) selecionada(s). Mínimo 1 para gerar laudo.")
                    col_a, col_b, col_dl = st.columns(3)
                    with col_a:
                        if st.button("✅ Selecionar Todas", key=f"sel_all_{req['id']}"):
                            st.session_state[f"_cmd_sel_all_{req['id']}"] = True
                            st.rerun()
                    with col_b:
                        if st.button("⬜ Desmarcar Todas", key=f"desel_all_{req['id']}"):
                            st.session_state[f"_cmd_sel_none_{req['id']}"] = True
                            st.rerun()
                    with col_dl:
                        from database.image_storage import get_image_bytes_and_filename
                        buf_zip = io.BytesIO()
                        with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                            for i, ref in enumerate(imagens_paths):
                                result = get_image_bytes_and_filename(ref)
                                if result:
                                    data, nome = result
                                    arcname = f"{i + 1}_{nome}"
                                    zf.writestr(arcname, data)
                        buf_zip.seek(0)
                        zip_bytes = buf_zip.getvalue()
                        if zip_bytes:
                            st.download_button(
                                "📦 Baixar todas",
                                data=zip_bytes,
                                file_name=f"requisicao_{req['id'][:8]}_imagens.zip",
                                mime="application/zip",
                                key=f"dl_zip_laudo_{req['id']}",
                                use_container_width=True,
                            )
            else:
                st.divider()

            # Botão para iniciar/parar edição
            col_btn_toggle, col_btn2, col_btn3, col_btn4 = st.columns(4)
            with col_btn_toggle:
                if is_editing:
                    if st.button("❌ Fechar Editor", key=f"close_edit_{req['id']}", use_container_width=True):
                        del st.session_state[editing_key]
                        st.rerun()
                else:
                    btn_label = "✏️ Editar Laudo" if laudo else "🤖 Gerar Laudo"
                    if st.button(btn_label, key=f"edit_{req['id']}", use_container_width=True):
                        # Se não há laudo, gerar com IA primeiro (usar apenas imagens selecionadas)
                        if not laudo:
                            try:
                                selected_paths = []
                                if imagens_paths and sel_key in st.session_state:
                                    selected_paths = [imagens_paths[i] for i in range(
                                        len(imagens_paths)) if st.session_state[sel_key][i]]
                                else:
                                    selected_paths = list(imagens_paths)
                                if not selected_paths:
                                    st.error("Selecione ao menos 1 imagem para gerar o laudo.")
                                    st.stop()
                                with st.spinner("🤖 Gerando laudo com IA..."):
                                    from ai.analyzer import load_images_for_analysis
                                    from ai.learning_system import LearningSystem
                                    images = load_images_for_analysis(selected_paths)
                                    if images:
                                        learning_system = LearningSystem()
                                        _obs_tex = "\n".join(
                                            o.get("texto", "").strip()
                                            for o in (req.get("observacoes_usuario") or [])
                                            if o.get("texto", "").strip()
                                        )
                                        paciente_info = {
                                            "especie": req.get("especie", ""),
                                            "raca": req.get("raca", ""),
                                            "idade": req.get("idade", ""),
                                            "sexo": req.get("sexo", ""),
                                            "historico_clinico": req.get("historico_clinico", "") or req.get("observacoes", ""),
                                            "suspeita_clinica": req.get("suspeita_clinica", ""),
                                            "regiao_estudo": req.get("regiao_estudo", ""),
                                            "observacoes_adicionais_usuario": _obs_tex,
                                        }
                                        texto_gerado, metadata = learning_system.generate_laudo(
                                            images, paciente_info, req["id"]
                                        )
                                        modelo_info = metadata.get("modelo_usado", "api_externa")
                                        if metadata.get("similaridade_casos", 0) > 0:
                                            st.info(
                                                f"🤖 Modelo: {modelo_info} | Similaridade: {metadata['similaridade_casos']:.2%}")
                                        laudo_id = laudo_model.create(
                                            requisicao_id=req["id"],
                                            texto=texto_gerado,
                                            texto_original=texto_gerado,
                                            status="pendente",
                                            modelo_usado=modelo_info,
                                            usado_api_externa=metadata.get(
                                                "usado_api_externa", True),
                                            similaridade_casos=metadata.get("similaridade_casos"),
                                            imagens_usadas=selected_paths,
                                        )
                                        st.session_state[f"laudo_metadata_{req['id']}"] = metadata
                                        st.session_state[f"laudo_paciente_info_{req['id']}"] = paciente_info
                                        st.success("✅ Laudo gerado com IA!")
                                        laudo = laudo_model.find_by_id(laudo_id)
                                    else:
                                        st.warning(
                                            "Nenhuma imagem válida. Criando laudo vazio para edição manual.")
                                        laudo_id = laudo_model.create(
                                            requisicao_id=req["id"],
                                            texto="",
                                            texto_original="",
                                            status="pendente",
                                            imagens_usadas=selected_paths,
                                        )
                                        laudo = laudo_model.find_by_id(laudo_id)
                            except Exception as e:
                                st.warning(f"⚠️ Erro ao gerar laudo: {str(e)}")
                                laudo_id = laudo_model.create(
                                    requisicao_id=req["id"],
                                    texto="",
                                    texto_original="",
                                    status="pendente",
                                )
                                laudo = laudo_model.find_by_id(laudo_id)
                        # Abrir editor
                        st.session_state[editing_key] = True
                        st.rerun()
            with col_btn2:
                pass  # Botão "Iniciar Análise" removido - fluxo direto para Gerar Laudo
            with col_btn3:
                if laudo and laudo.get("status") in ("pendente", "validado") and not is_editing:
                    if st.button("📤 Aprovar/Liberar", key=f"approve_{req['id']}", use_container_width=True):
                        with st.spinner("📤 Liberando laudo..."):
                            # Liberar laudo (calcula rating automaticamente)
                            laudo_model.release(laudo["id"], calcular_rating=True)
                            requisicao_model.update_status(req["id"], "liberado")

                            # Salvar dados de aprendizado
                            try:
                                from ai.learning_system import LearningSystem
                                learning_system = LearningSystem()

                                # Buscar metadata e contexto salvos
                                metadata = st.session_state.get(f"laudo_metadata_{req['id']}", {})
                                paciente_info = st.session_state.get(
                                    f"laudo_paciente_info_{req['id']}", {})

                                # Recarregar laudo para pegar rating calculado
                                laudo_atualizado = laudo_model.find_by_id(laudo["id"])
                                rating = laudo_atualizado.get("rating", 3)

                                # Salvar no sistema de aprendizado
                                if paciente_info:
                                    learning_system.save_learning_data(
                                        laudo_id=laudo["id"],
                                        requisicao_id=req["id"],
                                        contexto=paciente_info,
                                        texto_gerado=laudo.get(
                                            "texto_original_gerado", laudo.get("texto_original", "")),
                                        texto_final=laudo_atualizado.get("texto", ""),
                                        rating=rating,
                                        metadata=metadata
                                    )
                            except Exception as e:
                                st.warning(f"⚠️ Erro ao salvar dados de aprendizado: {str(e)}")

                            st.success("✅ Laudo liberado para o usuário!")
                            st.rerun()
            with col_btn4:
                if st.button("🗑️ Rejeitar", key=f"reject_{req['id']}", use_container_width=True):
                    requisicao_model.update_status(req["id"], "rejeitado")
                    st.success("Requisição rejeitada")
                    st.rerun()

            # Editor inline de laudo (quando is_editing = True)
            if is_editing:
                # Recarregar laudo (pode ter sido criado agora)
                laudo = laudo_model.find_by_requisicao(req["id"])
                if not laudo:
                    st.error("Erro: Laudo não encontrado. Feche o editor e tente novamente.")
                else:
                    imagens_paths = req.get("imagens", [])
                    st.divider()
                    st.subheader("✏️ Edição de Laudo")

                    # Layout: imagens à esquerda, editor fixo à direita
                    col_imgs, col_edit = st.columns([1.5, 1])

                    # Coluna de imagens (esquerda) - Grid de miniaturas com lightbox
                    with col_imgs:
                        st.subheader("🖼️ Imagens para conferência")

                        if imagens_paths:
                            from ai.analyzer import load_images_for_analysis

                            # CSS e JavaScript para lightbox
                            lightbox_id = f"lightbox_{req['id'][:8]}"
                            st.markdown(f"""
                                <style>
                                /* Remover TODOS os espaços brancos dos containers de imagem - CSS Global */
                                div[id^="img_container_{req['id'][:8]}"] .stImage,
                                div[id^="img_container_{req['id'][:8]}"] .stImage > div,
                                div[id^="img_container_{req['id'][:8]}"] .stImage > div > div,
                                div[id^="img_container_{req['id'][:8]}"] .stImage > div > div > div,
                                div[id^="img_container_{req['id'][:8]}"] .stImage > div > div > div > div {{
                                    padding-top: 0 !important;
                                    margin-top: 0 !important;
                                    padding-bottom: 0 !important;
                                    margin-bottom: 0 !important;
                                    padding: 0 !important;
                                    margin: 0 !important;
                                }}
                                
                                div[id^="img_container_{req['id'][:8]}"] .stImage img {{
                                    margin: 0 !important;
                                    padding: 0 !important;
                                    display: block !important;
                                }}
                                
                                /* Remover espaços do primeiro elemento dentro do container */
                                div[id^="img_container_{req['id'][:8]}"] > div:first-child {{
                                    margin-top: 0 !important;
                                    padding-top: 0 !important;
                                }}
                                
                                /* Grid de miniaturas - 4 colunas */
                                .thumb-grid-{req['id'][:8]} {{
                                    display: grid !important;
                                    grid-template-columns: repeat(4, 1fr) !important;
                                    gap: 1.5rem !important;
                                    margin-bottom: 1.5rem !important;
                                    width: 100% !important;
                                }}
                                
                                /* Garantir que o container do Streamlit não interfira */
                                .thumb-grid-{req['id'][:8]} > * {{
                                    display: block !important;
                                }}
                                
                                .thumb-item-{req['id'][:8]} {{
                                    cursor: pointer;
                                    border: 2px solid #e0e0e0;
                                    border-radius: 8px;
                                    padding: 0.75rem;
                                    transition: all 0.3s;
                                    background: #f5f5f5;
                                }}
                                
                                .thumb-item-{req['id'][:8]}:hover {{
                                    border-color: #2e7d32;
                                    transform: scale(1.05);
                                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                                }}
                                
                                .thumb-item-{req['id'][:8]} img {{
                                    width: 100%;
                                    height: 220px;
                                    object-fit: contain;
                                    border-radius: 4px;
                                }}
                                
                                @media (max-width: 1400px) {{
                                    .thumb-grid-{req['id'][:8]} {{
                                        grid-template-columns: repeat(3, 1fr);
                                    }}
                                }}
                                
                                @media (max-width: 1000px) {{
                                    .thumb-grid-{req['id'][:8]} {{
                                        grid-template-columns: repeat(2, 1fr);
                                    }}
                                }}
                                
                                /* Lightbox Modal */
                                #{lightbox_id} {{
                                    display: none;
                                    position: fixed;
                                    z-index: 2000;
                                    left: 0;
                                    top: 0;
                                    width: 100%;
                                    height: 100%;
                                    background-color: rgba(0,0,0,0.9);
                                    overflow: auto;
                                }}
                                
                                #{lightbox_id} .lightbox-content {{
                                    margin: auto;
                                    display: block;
                                    width: 90%;
                                    max-width: 1200px;
                                    margin-top: 50px;
                                    animation: zoom 0.3s;
                                }}
                                
                                @keyframes zoom {{
                                    from {{transform: scale(0.5)}}
                                    to {{transform: scale(1)}}
                                }}
                                
                                #{lightbox_id} .close {{
                                    position: absolute;
                                    top: 15px;
                                    right: 35px;
                                    color: #f1f1f1;
                                    font-size: 40px;
                                    font-weight: bold;
                                    cursor: pointer;
                                }}
                                
                                #{lightbox_id} .close:hover {{
                                    color: #bbb;
                                }}
                                
                                #{lightbox_id} .lightbox-caption {{
                                    margin: auto;
                                    display: block;
                                    width: 90%;
                                    max-width: 1200px;
                                    text-align: center;
                                    color: #ccc;
                                    padding: 10px 0;
                                    height: 40px;
                                }}
                                
                                #{lightbox_id} .lightbox-nav {{
                                    position: absolute;
                                    top: 50%;
                                    transform: translateY(-50%);
                                    background-color: rgba(0,0,0,0.5);
                                    color: white;
                                    border: none;
                                    padding: 16px;
                                    font-size: 20px;
                                    cursor: pointer;
                                    border-radius: 4px;
                                }}
                                
                                #{lightbox_id} .lightbox-nav:hover {{
                                    background-color: rgba(0,0,0,0.8);
                                }}
                                
                                #{lightbox_id} .lightbox-prev {{
                                    left: 20px;
                                }}
                                
                                #{lightbox_id} .lightbox-next {{
                                    right: 20px;
                                }}
                                </style>
                                
                                <div id="{lightbox_id}" class="lightbox">
                                    <span class="close">&times;</span>
                                    <button class="lightbox-nav lightbox-prev">&#10094;</button>
                                    <button class="lightbox-nav lightbox-next">&#10095;</button>
                                    <img class="lightbox-content" id="lightbox-img">
                                    <div class="lightbox-caption" id="lightbox-caption"></div>
                                </div>
                                
                                <script>
                                // Este código será substituído pelo novo sistema de lightbox abaixo
                                </script>
                            """, unsafe_allow_html=True)

                            # Preparar todas as imagens para o grid
                            from ai.analyzer import load_images_for_analysis
                            from database.image_storage import get_filename
                            import base64
                            from io import BytesIO

                            # Preparar dados das imagens e converter para base64
                            images_data = []
                            for i, ref in enumerate(imagens_paths):
                                nome = get_filename(ref)
                                preview = None

                                try:
                                    loaded = load_images_for_analysis([ref])
                                    preview = loaded[0] if loaded else None
                                except Exception:
                                    pass

                                img_data_url = None
                                if preview is not None:
                                    buf = BytesIO()
                                    preview.save(buf, format='PNG')
                                    buf.seek(0)
                                    img_base64 = base64.b64encode(buf.read()).decode()
                                    img_data_url = f"data:image/png;base64,{img_base64}"

                                images_data.append({
                                    'path': ref,
                                    'nome': nome,
                                    'preview': preview,
                                    'data_url': img_data_url,
                                    'index': i
                                })

                            # Inicializar array de imagens para o lightbox E definir função openLightbox ANTES de renderizar
                            st.markdown(f"""
                                <script>
                                window.lightboxImages_{req['id'][:8]} = [];
                                
                                // Definir função openLightbox GLOBALMENTE antes de renderizar as imagens
                                window.openLightbox_{req['id'][:8]} = function(index) {{
                                    const images = window.lightboxImages_{req['id'][:8]} || [];
                                    if (images.length === 0 || !images[index]) {{
                                        console.error('Lightbox: imagens não disponíveis ou índice inválido', index, images.length);
                                        return;
                                    }}
                                    
                                    const lightbox = document.getElementById('{lightbox_id}');
                                    const lightboxImg = document.getElementById('lightbox-img');
                                    const lightboxCaption = document.getElementById('lightbox-caption');
                                    
                                    if (lightbox && lightboxImg && lightboxCaption) {{
                                        lightboxImg.src = images[index].src;
                                        lightboxCaption.textContent = images[index].caption;
                                        lightbox.style.display = 'block';
                                        window.currentLightboxIndex_{req['id'][:8]} = index;
                                    }} else {{
                                        console.error('Lightbox: elementos não encontrados', {{lightbox: !!lightbox, lightboxImg: !!lightboxImg, lightboxCaption: !!lightboxCaption}});
                                    }}
                                }};
                            """, unsafe_allow_html=True)

                            # Criar grid usando st.columns - 4 colunas
                            num_cols = 4
                            for row_start in range(0, len(images_data), num_cols):
                                cols = st.columns(num_cols)
                                row_images = images_data[row_start:row_start + num_cols]

                                for col_idx, col in enumerate(cols):
                                    if col_idx < len(row_images):
                                        img_data = row_images[col_idx]
                                        nome = img_data['nome']
                                        preview = img_data['preview']
                                        img_data_url = img_data['data_url']

                                        with col:
                                            if preview is not None and img_data_url:
                                                # Renderizar imagem diretamente em HTML (sem usar st.image para evitar espaços)
                                                # O array do lightbox será preenchido após o loop
                                                container_key = f"img_container_{req['id']}_{img_data['index']}"
                                                nome_display = nome[:40] + \
                                                    ('...' if len(nome) > 40 else '')

                                                # Renderizar tudo em HTML puro para evitar espaços do Streamlit
                                                # Usar onclick inline para evitar problemas com JavaScript sendo renderizado como texto
                                                st.markdown(f"""
                                                    <div id="{container_key}" onclick="if(window.openLightbox_{req['id'][:8]}){{window.openLightbox_{req['id'][:8]}({img_data['index']});}}" style="cursor: pointer; border: 2px solid #e0e0e0; border-radius: 8px; padding: 0.75rem; background: #f5f5f5; margin-bottom: 1rem; transition: all 0.3s; overflow: hidden;" onmouseover="this.style.borderColor='#2e7d32'; this.style.transform='scale(1.02)'" onmouseout="this.style.borderColor='#e0e0e0'; this.style.transform='scale(1)'">
                                                        <img src="{img_data_url}" alt="Imagem {img_data['index'] + 1}: {nome}" style="width: 100%; height: auto; max-height: 250px; object-fit: contain; display: block; margin: 0; padding: 0; border-radius: 4px;">
                                                        <div style="text-align: center; margin-top: 0.5rem; font-size: 0.85rem; color: #666; font-weight: 500;">
                                                            {nome_display}
                                                        </div>
                                                    </div>
                                                """, unsafe_allow_html=True)
                                            else:
                                                nome_display = nome[:30] + \
                                                    ('...' if len(nome) > 30 else '')
                                                st.info(f"📄 {nome_display}\n\nPrévia indisponível")

                                    # Preencher colunas vazias na última linha
                                    if col_idx >= len(row_images):
                                        with col:
                                            st.empty()

                            # Preencher array do lightbox com todas as imagens após o loop
                            import json
                            images_js_items = []
                            for img in images_data:
                                if img.get('data_url'):
                                    caption = f"Imagem {img['index'] + 1}: {img['nome']}"
                                    images_js_items.append(
                                        f"{{src: {json.dumps(img['data_url'])}, caption: {json.dumps(caption)}}}"
                                    )
                            images_js_array = ",\n".join(images_js_items)
                            st.markdown(f"""
                                <script>
                                // Preencher array do lightbox com todas as imagens
                                window.lightboxImages_{req['id'][:8]} = [
                                    {images_js_array}
                                ];
                                </script>
                            """, unsafe_allow_html=True)

                            # JavaScript do lightbox - funções de navegação
                            st.markdown(f"""
                                <script>
                                // Funções de navegação do lightbox
                                (function() {{
                                    const lightbox = document.getElementById('{lightbox_id}');
                                    if (!lightbox) return;
                                    
                                    const lightboxImg = document.getElementById('lightbox-img');
                                    const lightboxCaption = document.getElementById('lightbox-caption');
                                    const closeBtn = lightbox.querySelector('.close');
                                    const prevBtn = lightbox.querySelector('.lightbox-prev');
                                    const nextBtn = lightbox.querySelector('.lightbox-next');
                                    
                                    window.currentLightboxIndex_{req['id'][:8]} = 0;
                                    
                                    function updateLightbox() {{
                                        const images = window.lightboxImages_{req['id'][:8]} || [];
                                        const idx = window.currentLightboxIndex_{req['id'][:8]};
                                        if (images[idx] && lightboxImg && lightboxCaption) {{
                                            lightboxImg.src = images[idx].src;
                                            lightboxCaption.textContent = images[idx].caption;
                                        }}
                                    }}
                                    
                                    function nextImage() {{
                                        const images = window.lightboxImages_{req['id'][:8]} || [];
                                        if (images.length === 0) return;
                                        window.currentLightboxIndex_{req['id'][:8]} = (window.currentLightboxIndex_{req['id'][:8]} + 1) % images.length;
                                        updateLightbox();
                                    }}
                                    
                                    function prevImage() {{
                                        const images = window.lightboxImages_{req['id'][:8]} || [];
                                        if (images.length === 0) return;
                                        window.currentLightboxIndex_{req['id'][:8]} = (window.currentLightboxIndex_{req['id'][:8]} - 1 + images.length) % images.length;
                                        updateLightbox();
                                    }}
                                    
                                    function closeLightbox() {{
                                        lightbox.style.display = 'none';
                                    }}
                                    
                                    if (closeBtn) closeBtn.onclick = closeLightbox;
                                    if (nextBtn) nextBtn.onclick = nextImage;
                                    if (prevBtn) prevBtn.onclick = prevImage;
                                    
                                    lightbox.onclick = function(e) {{
                                        if (e.target === lightbox) closeLightbox();
                                    }};
                                    
                                    document.addEventListener('keydown', function(e) {{
                                        if (lightbox.style.display === 'block') {{
                                            if (e.key === 'Escape') closeLightbox();
                                            if (e.key === 'ArrowRight') nextImage();
                                            if (e.key === 'ArrowLeft') prevImage();
                                        }}
                                    }});
                                }})();
                                </script>
                            """, unsafe_allow_html=True)

                            # Baixar todas as imagens em um único ZIP
                            from database.image_storage import get_image_bytes_and_filename
                            buf = io.BytesIO()
                            added = 0
                            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                                for i, ref in enumerate(imagens_paths):
                                    result = get_image_bytes_and_filename(ref)
                                    if result:
                                        data, nome = result
                                        arcname = f"{i + 1}_{nome}"
                                        zf.writestr(arcname, data)
                                        added += 1
                            buf.seek(0)
                            zip_bytes = buf.getvalue()
                            if added > 0 and zip_bytes:
                                st.download_button(
                                    "📦 Baixar todas as imagens (ZIP)",
                                    data=zip_bytes,
                                    file_name=f"requisicao_{req['id'][:8]}_imagens.zip",
                                    mime="application/zip",
                                    key=f"dl_zip_inline_{req['id']}",
                                    use_container_width=True,
                                )
                            st.caption(
                                "**💡 Dica:** Clique em uma miniatura para ver a imagem em tamanho grande. Use as setas do teclado ou os botões para navegar. **DICOM:** baixe o arquivo e abra em um leitor local (ex.: RadiAnt, OsiriX, 3D Slicer) para visualização com janela/nível, zoom e medições."
                            )
                        else:
                            st.info("Nenhuma imagem associada a esta requisição.")

                    # Coluna do editor (direita) - será fixada via JavaScript
                    with col_edit:
                        editor_key = f"laudo_edit_inline_{laudo['id']}"
                        st.subheader("✏️ Editar Laudo")
                        # Contexto da requisição (clínica e veterinário sempre visíveis na geração do laudo; fallback pelo usuário)
                        _clinica_ctx, _vet_ctx = _req_clinica_vet_display(req)
                        st.caption(
                            f"**Requisição:** {(req.get('paciente') or '—').upper()} · **Clínica:** {(_clinica_ctx or '—').upper()} · **M.V.:** {(_vet_ctx or '—').upper()}")

                        # CORREÇÕES PARA IA (opcional) - para gerar laudo com correções do especialista
                        correcoes_key = f"correcoes_ia_{laudo['id']}"
                        clear_flag_key = f"_clear_{correcoes_key}"
                        # Não modificar correcoes_key após o widget existir; usar flag para limpar no rerun
                        correcoes_initial = "" if st.session_state.pop(
                            clear_flag_key, False) else st.session_state.get(correcoes_key, "")
                        correcoes_texto = st.text_area(
                            "🔧 CORREÇÕES PARA IA (opcional)",
                            value=correcoes_initial,
                            height=80,
                            max_chars=500,
                            placeholder='Ex: "A lesão está no membro ESQUERDO, não direito"',
                            key=correcoes_key,
                            help="Descreva as correções para a IA gerar o laudo. Máx. 500 caracteres.",
                        )
                        st.caption(f"{len(correcoes_texto)}/500 caracteres")

                        # Editor do laudo (alterações são salvas ao Liberar ou ao gerar com correções)
                        # Texto já formatado: converte \n, \t literais em quebras/tabs reais (evita caracteres especiais da API)
                        texto_laudo_formatado = _formatar_texto_laudo_para_edicao(
                            laudo.get("texto", ""))
                        texto_editado = st.text_area(
                            "📝 Conteúdo do laudo",
                            value=texto_laudo_formatado,
                            height=500,
                            key=editor_key,
                        )

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("🔄 Gerar Laudo c/ Correções", use_container_width=True, key=f"gen_inline_{laudo['id']}"):
                                if not correcoes_texto or not correcoes_texto.strip():
                                    st.warning(
                                        "Digite as correções no campo acima antes de regenerar.")
                                else:
                                    try:
                                        with st.spinner("Gerando laudo com correções..."):
                                            from ai.learning_system import LearningSystem
                                            ls = LearningSystem()
                                            imagens_usadas = laudo.get(
                                                "imagens_usadas") or req.get("imagens") or []
                                            novo_texto, _ = ls.regenerate_with_corrections(
                                                laudo["id"], req["id"], correcoes_texto.strip(
                                                ), imagens_usadas
                                            )
                                            laudo_model.update(laudo["id"], {
                                                "texto": novo_texto,
                                                "regenerado_com_correcoes": True,
                                                "rating": 2,
                                            })
                                            st.session_state[clear_flag_key] = True
                                        st.success(
                                            "Laudo gerado com correções! (rating 2/5 – precisou correção)")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao gerar: {str(e)}")
                        with col2:
                            if st.button("📤 Liberar", use_container_width=True, key=f"lib_inline_{laudo['id']}"):
                                with st.spinner("📤 Liberando laudo..."):
                                    # Salva o conteúdo atual antes de liberar (não exige botão "Salvar" separado)
                                    if texto_editado != texto_laudo_formatado:
                                        user = get_current_user()
                                        laudo_model.registrar_edicao(
                                            laudo["id"],
                                            texto_editado,
                                            user["id"] if user else None
                                        )
                                    else:
                                        laudo_model.update(laudo["id"], {"texto": texto_editado})
                                    laudo_model.release(laudo["id"], calcular_rating=True)
                                    requisicao_model.update_status(req["id"], "liberado")

                                    # Salvar dados de aprendizado (inclui laudos regenerados com correções)
                                    try:
                                        from ai.learning_system import LearningSystem
                                        ls = LearningSystem()
                                        paciente_info = {
                                            "especie": req.get("especie", ""),
                                            "raca": req.get("raca", ""),
                                            "idade": req.get("idade", ""),
                                            "sexo": req.get("sexo", ""),
                                            "historico_clinico": req.get("historico_clinico", "") or req.get("observacoes", ""),
                                            "suspeita_clinica": req.get("suspeita_clinica", ""),
                                            "regiao_estudo": req.get("regiao_estudo", ""),
                                            "observacoes_adicionais_usuario": "\n".join(
                                                o.get("texto", "").strip()
                                                for o in (req.get("observacoes_usuario") or [])
                                                if o.get("texto", "").strip()
                                            ),
                                        }
                                        laudo_apos_release = laudo_model.find_by_id(laudo["id"])
                                        rating = laudo_apos_release.get("rating", 3)
                                        metadata = st.session_state.get(f"laudo_metadata_{req['id']}", {})
                                        if not metadata:
                                            metadata = {
                                                "modelo_usado": laudo.get("modelo_usado", "api_externa"),
                                                "usado_api_externa": laudo.get("usado_api_externa", True),
                                                "similaridade_casos": laudo.get("similaridade_casos"),
                                                "casos_similares": [],
                                            }
                                        ls.save_learning_data(
                                            laudo_id=laudo["id"],
                                            requisicao_id=req["id"],
                                            contexto=paciente_info,
                                            texto_gerado=laudo.get("texto_original_gerado", laudo.get("texto_original", "")),
                                            texto_final=laudo_apos_release.get("texto", ""),
                                            rating=rating,
                                            metadata=metadata,
                                        )
                                    except Exception as e:
                                        st.warning(f"⚠️ Erro ao salvar aprendizado: {str(e)}")

                                    st.success(
                                        "✅ Laudo liberado para o usuário! Ele poderá visualizar e fazer download agora.")
                                    st.balloons()
                                    del st.session_state[editing_key]
                                    st.rerun()
                        with col3:
                            if st.button("❌ Cancelar", use_container_width=True, key=f"cancel_inline_{laudo['id']}"):
                                del st.session_state[editing_key]
                                st.rerun()

                    # JavaScript para fixar a coluna do editor após renderização
                    st.markdown(f"""
                        <script>
                        (function() {{
                            function fixEditorColumn() {{
                                // Encontrar o textarea do editor pelo key
                                const textarea = document.querySelector('textarea');
                                if (!textarea) return;
                                
                                // Encontrar a coluna que contém este textarea
                                let col = textarea.closest('[data-testid="column"]');
                                if (!col) {{
                                    let parent = textarea.parentElement;
                                    let depth = 0;
                                    while (parent && parent !== document.body && depth < 20) {{
                                        if (parent.hasAttribute && parent.getAttribute('data-testid') === 'column') {{
                                            col = parent;
                                            break;
                                        }}
                                        parent = parent.parentElement;
                                        depth++;
                                    }}
                                }}
                                
                                if (col) {{
                                    // Verificar se é a segunda coluna
                                    const columnsContainer = col.parentElement;
                                    if (columnsContainer && columnsContainer.getAttribute('data-testid') === 'stColumns') {{
                                        const cols = columnsContainer.querySelectorAll('[data-testid="column"]');
                                        if (cols.length >= 2 && cols[1] === col) {{
                                            // Aplicar position fixed
                                            col.style.cssText = `
                                                position: fixed !important;
                                                top: 100px !important;
                                                right: 20px !important;
                                                width: 45% !important;
                                                max-width: 550px !important;
                                                max-height: calc(100vh - 120px) !important;
                                                background-color: #ffffff !important;
                                                border: 2px solid #2e7d32 !important;
                                                border-radius: 8px !important;
                                                box-shadow: 0 4px 16px rgba(0,0,0,0.2) !important;
                                                z-index: 1000 !important;
                                                padding: 1.5rem !important;
                                                overflow-y: auto !important;
                                            `;
                                            
                                            // Ajustar margem da primeira coluna
                                            if (cols[0]) {{
                                                cols[0].style.marginRight = 'calc(45% + 30px)';
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                            
                            // Executar após renderização
                            setTimeout(fixEditorColumn, 100);
                            setTimeout(fixEditorColumn, 500);
                            setTimeout(fixEditorColumn, 1000);
                            
                            // Observer
                            const observer = new MutationObserver(function() {{
                                setTimeout(fixEditorColumn, 50);
                            }});
                            observer.observe(document.body, {{ childList: true, subtree: true }});
                        }})();
                        </script>
                    """, unsafe_allow_html=True)

elif page == "Nova Requisição":
    st.header("📤 Nova Requisição de Laudo (Administrador)")
    st.caption("Cadastre requisições em nome de clínicas. Selecione a clínica e o veterinário responsável. O campo criado_por registrará seu ID para auditoria.")

    st.markdown("""
        <style>
        .nr-block { background: #f8faf8; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; border-left: 4px solid #2e7d32; }
        .main .block-container input[type="text"], .main .block-container textarea { text-transform: uppercase; }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.get('admin_requisicao_enviada') and st.session_state.get('admin_requisicao_info'):
        info = st.session_state['admin_requisicao_info']
        st.success(f"✅ **Requisição enviada com sucesso!** ID: {info.get('req_id', '')[:8]}")
        st.info("📝 A requisição entrou na fila para geração do laudo via IA.")
        if st.button("✖️ Fechar", key="admin_close_requisicao_feedback"):
            del st.session_state['admin_requisicao_enviada']
            del st.session_state['admin_requisicao_info']
            st.rerun()
        st.markdown("---")

    # Prefixo para keys do formulário admin (evitar conflito com user dashboard)
    pref = "admin_nr_"
    for k in [f"{pref}paciente", f"{pref}tutor", f"{pref}especie", f"{pref}idade", f"{pref}raca",
              f"{pref}sexo", f"{pref}medico_vet", f"{pref}regiao", f"{pref}suspeita", f"{pref}historico",
              f"{pref}tipo_exame", f"{pref}veterinario_id", f"{pref}clinica_id"]:
        if k not in st.session_state:
            st.session_state[k] = ""
    if f"{pref}plantao" not in st.session_state or st.session_state[f"{pref}plantao"] == "":
        st.session_state[f"{pref}plantao"] = "Não"
    if f"{pref}sexo" not in st.session_state or st.session_state[f"{pref}sexo"] == "":
        st.session_state[f"{pref}sexo"] = "Macho"
    if f"{pref}data" not in st.session_state:
        st.session_state[f"{pref}data"] = now().date()

    clinicas_list = clinica_model.get_all(apenas_ativas=True)
    if not clinicas_list:
        st.warning(
            "⚠️ Nenhuma clínica ativa cadastrada. Cadastre clínicas em **Clínicas e Usuários** antes de criar requisições.")
    else:
        st.subheader("📋 Clínica e Veterinário")
        clinica_opcoes = [
            (c.get("nome", "") or f"Clínica {c.get('id', '')[:8]}", c.get("id", "")) for c in clinicas_list]
        idx_clinica = 0
        clinica_id_sel = st.session_state.get(f"{pref}clinica_id", "")
        if clinica_id_sel:
            for i, (_, cid) in enumerate(clinica_opcoes):
                if cid == clinica_id_sel:
                    idx_clinica = i
                    break
        clinica_nome_sel = st.selectbox(
            "🏥 Clínica *",
            range(len(clinica_opcoes)),
            index=idx_clinica,
            format_func=lambda i: clinica_opcoes[i][0] if i < len(clinica_opcoes) else "",
            key=f"{pref}clinica_select",
        )
        clinica_id_sel = clinica_opcoes[clinica_nome_sel][1]
        clinica_nome = clinica_opcoes[clinica_nome_sel][0]
        st.session_state[f"{pref}clinica_id"] = clinica_id_sel

        veterinarios_list = veterinario_model.find_by_clinica(
            clinica_id_sel, apenas_ativos=True) if clinica_id_sel else []
        medico_vet = ""
        veterinario_id_selecionado = ""
        if len(veterinarios_list) == 0:
            medico_vet = "Equipe " + clinica_nome if clinica_nome else ""
            st.caption(
                f"**Solicitante:** {clinica_nome}. Nenhum veterinário cadastrado nesta clínica.")
        elif len(veterinarios_list) == 1:
            vet_um = veterinarios_list[0]
            medico_vet = (vet_um or {}).get("nome", "") or ("Equipe " + clinica_nome)
            veterinario_id_selecionado = (vet_um or {}).get("id", "")
            st.text_input("Veterinário requisitante", value=medico_vet, disabled=True,
                          key=f"{pref}vet_display", label_visibility="collapsed")
            st.caption(f"**Solicitante:** {clinica_nome} – único veterinário cadastrado.")
        else:
            options_vet = [
                v.get("nome", "") or f"Veterinário {i + 1}" for i, v in enumerate(veterinarios_list)]
            nr_vet_id = st.session_state.get(f"{pref}veterinario_id", "")
            idx_v = 0
            if nr_vet_id:
                for i, v in enumerate(veterinarios_list):
                    if v.get("id") == nr_vet_id:
                        idx_v = i
                        break
            sel_v = st.selectbox(
                "👨‍⚕️ Veterinário requisitante",
                range(len(veterinarios_list)),
                index=idx_v,
                format_func=lambda i: options_vet[i] if i < len(options_vet) else "",
                key=f"{pref}vet_select",
            )
            vet_escolhido = veterinarios_list[sel_v]
            medico_vet = (vet_escolhido or {}).get("nome", "")
            veterinario_id_selecionado = (vet_escolhido or {}).get("id", "")
            st.session_state[f"{pref}veterinario_id"] = veterinario_id_selecionado or ""
            st.caption(
                f"**Solicitante:** {clinica_nome} · {len(veterinarios_list)} veterinário(s).")

        st.subheader("📋 Dados do Paciente e da Requisição")
        paciente = st.text_input(
            "🐾 Nome do Paciente *", value=st.session_state.get(f"{pref}paciente", ""), key=f"{pref}paciente")
        ESPECIES_OPCOES = ["", "Canino", "Felino", "Ave", "Silvestre"]
        idx_especie = 0
        if st.session_state.get(f"{pref}especie", "") in ESPECIES_OPCOES:
            idx_especie = ESPECIES_OPCOES.index(st.session_state.get(f"{pref}especie", ""))
        especie = st.selectbox("🐕 Espécie", options=ESPECIES_OPCOES, index=idx_especie, key=f"{pref}especie",
                               format_func=lambda x: "Selecione a espécie" if x == "" else x)
        idade = st.text_input("📅 Idade", value=st.session_state.get(
            f"{pref}idade", ""), key=f"{pref}idade")
        raca = st.text_input("🏷️ Raça", value=st.session_state.get(
            f"{pref}raca", ""), key=f"{pref}raca")
        sexo = st.radio("Sexo", ["Macho", "Fêmea"], index=0 if st.session_state.get(f"{pref}sexo") == "Macho" else 1,
                        key=f"{pref}sexo", horizontal=True)
        tutor = st.text_input("👤 Nome do Tutor(a) *",
                              value=st.session_state.get(f"{pref}tutor", ""), key=f"{pref}tutor")
        regiao = st.text_input("📍 Região de estudo", value=st.session_state.get(
            f"{pref}regiao", ""), key=f"{pref}regiao")
        suspeita = st.text_input("🔬 Suspeita clínica", value=st.session_state.get(
            f"{pref}suspeita", ""), key=f"{pref}suspeita")
        plantao = st.radio("Plantão", ["Sim", "Não"], index=1,
                           key=f"{pref}plantao", horizontal=True)
        tipo_exame = st.selectbox(
            "📋 Tipo de exame *", ["raio-x", "ultrassom"], index=0, key=f"{pref}tipo_exame")
        data_exame = st.date_input("📆 Data", value=st.session_state.get(
            f"{pref}data", now().date()), key=f"{pref}data")
        historico = st.text_area("📝 Histórico Clínico", value=st.session_state.get(f"{pref}historico", ""),
                                 height=120, key=f"{pref}historico")

        st.subheader("📷 Imagens do Exame")
        upload_key_admin = f"{pref}upload_{st.session_state.get('admin_upload_counter', 0)}"
        uploaded_files = st.file_uploader(
            "Selecione as imagens (JPG, PNG, DICOM). Múltiplas imagens permitidas.",
            type=["jpg", "jpeg", "png", "dcm", "dicom", "bmp", "tiff"],
            accept_multiple_files=True,
            key=upload_key_admin,
        )
        if uploaded_files:
            st.caption(f"✅ {len(uploaded_files)} arquivo(s) anexado(s).")

        def _upper(s):
            return (s or "").strip().upper() if isinstance(s, str) else s

        enviar = st.button("📤 Enviar Requisição", type="primary",
                           key=f"{pref}enviar", use_container_width=True)
        c1, c2 = st.columns(2)
        with c1:
            limpar = st.button("🗑️ Limpar formulário",
                               key=f"{pref}limpar", use_container_width=True)

        if limpar:
            for k in list(st.session_state.keys()):
                if k.startswith(pref) and k not in (f"{pref}enviar", f"{pref}limpar"):
                    del st.session_state[k]
            st.session_state[f"{pref}data"] = now().date()
            st.session_state[f"{pref}plantao"] = "Não"
            st.session_state[f"{pref}sexo"] = "Macho"
            st.session_state[f"{pref}tipo_exame"] = "raio-x"
            st.session_state["admin_upload_counter"] = st.session_state.get(
                "admin_upload_counter", 0) + 1
            st.rerun()

        if enviar:
            if not paciente or not tutor:
                st.error("Preencha o Nome do Paciente e o Nome do Tutor(a).")
            elif not uploaded_files:
                st.error("Selecione ao menos uma imagem do exame.")
            else:
                with st.spinner("📤 Enviando requisição e salvando imagens..."):
                    admin_id = st.session_state.get("user_id")
                    from database.image_storage import save_image
                    imagens_refs = []
                    for f in uploaded_files:
                        try:
                            data = f.getbuffer().tobytes()
                            image_id = save_image(data, f.name, metadata={"admin_id": admin_id})
                            imagens_refs.append(image_id)
                        except Exception as e:
                            log.exception("Erro ao salvar imagem admin no GridFS %s: %s", f.name, e)
                            raise

                    data_exame_dt = combine_date_local(data_exame) if data_exame else now()

                    try:
                        req_id = requisicao_model.create(
                            user_id=admin_id,
                            imagens=imagens_refs,
                            paciente=_upper(paciente),
                            tutor=_upper(tutor),
                            clinica=clinica_nome,
                            tipo_exame=tipo_exame,
                            observacoes=_upper(historico),
                            especie=especie,
                            idade=idade,
                            raca=_upper(raca),
                            sexo=sexo,
                            medico_veterinario_solicitante=medico_vet,
                            regiao_estudo=_upper(regiao),
                            suspeita_clinica=_upper(suspeita),
                            plantao=plantao,
                            historico_clinico=_upper(historico),
                            data_exame=data_exame_dt,
                            status="pendente",
                            clinica_id=clinica_id_sel,
                            veterinario_id=veterinario_id_selecionado or None,
                        )
                        st.session_state["admin_requisicao_enviada"] = True
                        st.session_state["admin_requisicao_info"] = {
                            "req_id": req_id, "paciente": paciente}
                        for k in list(st.session_state.keys()):
                            if k.startswith(pref) and k not in (f"{pref}enviar", f"{pref}limpar"):
                                del st.session_state[k]
                        st.session_state[f"{pref}data"] = now().date()
                        st.session_state[f"{pref}plantao"] = "Não"
                        st.session_state[f"{pref}sexo"] = "Macho"
                        st.session_state["admin_upload_counter"] = st.session_state.get(
                            "admin_upload_counter", 0) + 1
                        st.rerun()
                    except Exception as e:
                        log.exception("Erro ao criar requisição admin após upload: %s", e)
                        st.error(f"Erro ao criar requisição: {str(e)}")
                        import traceback as _tb
                        _tb.print_exc()

elif page == "Clínicas e Usuários":
    st.header("🏥 Clínicas e Usuários")
    st.caption("Cadastre clientes (clínicas) com conta de acesso. Cada clínica = 1 login; adicione veterinários para o formulário de requisições.")

    # Verificar se há um usuário sendo visualizado
    if st.session_state.get('viewing_user'):
        user_id = st.session_state.get('viewing_user')
        user = user_model.find_by_id(user_id)

        if user:
            st.subheader(f"📊 Detalhes do Usuário: {user.get('nome', user.get('username'))}")

            if st.button("← Voltar para Lista", key="back_to_list"):
                del st.session_state['viewing_user']
                st.rerun()

            st.divider()

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Informações Básicas")
                st.write(f"**Usuário (login):** {user.get('username')}")
                st.write(f"**E-mail:** {user.get('email')}")
                st.write(f"**Nome Completo:** {user.get('nome', 'N/A')}")
                st.write(
                    f"**Tipo:** {'👨‍⚕️ Administrador' if user.get('role') == 'admin' else '👤 Cliente'}")
                # Clínica (quando o usuário é cliente vinculado a uma clínica)
                if user.get("clinica_id"):
                    _clinica_user = clinica_model.find_by_id(user["clinica_id"])
                    clinica_nome_user = (_clinica_user or {}).get("nome", "") or "—"
                    st.write(f"**Clínica:** {clinica_nome_user}")
                else:
                    st.write("**Clínica:** —")
                st.write(f"**Status:** {'✅ Ativo' if user.get('ativo', True) else '🚫 Inativo'}")
                st.write(
                    f"**Primeiro Acesso:** {'⚠️ Pendente' if user.get('primeiro_acesso', False) else '✅ Concluído'}")
                st.write(f"**Cadastrado em:** {user.get('created_at', 'N/A')}")
                st.write(f"**Última atualização:** {user.get('updated_at', 'N/A')}")

            with col2:
                st.markdown("### Estatísticas")
                reqs = requisicao_model.find_by_user(user['id'])
                laudos = laudo_model.find_by_user(user['id'])
                laudos_liberados = [l for l in laudos if l.get('status') == 'liberado']

                st.metric("📋 Total de Requisições", len(reqs))
                st.metric("📝 Total de Laudos", len(laudos))
                st.metric("✅ Laudos Liberados", len(laudos_liberados))
                st.metric("⏳ Laudos Pendentes", len(
                    [l for l in laudos if l.get('status') == 'pendente']))

            st.divider()

            # Mostrar senha temporária se ainda for primeiro acesso
            if user.get('primeiro_acesso', False) and user.get('senha_temporaria'):
                st.warning(f"⚠️ **Senha Temporária Ativa:** `{user.get('senha_temporaria')}`")
                st.info("O usuário ainda não alterou a senha. Compartilhe essa senha temporária com ele.")

            st.divider()

            # Ações rápidas
            col_act1, col_act2, col_act3 = st.columns(3)
            with col_act1:
                if user.get('ativo'):
                    if st.button("🚫 Desativar Usuário", key=f"deactivate_detail_{user['id']}", use_container_width=True):
                        user_model.update(user['id'], {"ativo": False})
                        st.success("Usuário desativado")
                        st.rerun()
                else:
                    if st.button("✅ Ativar Usuário", key=f"activate_detail_{user['id']}", use_container_width=True):
                        user_model.update(user['id'], {"ativo": True})
                        st.success("Usuário ativado")
                        st.rerun()

            with col_act2:
                current_user = get_current_user()
                if current_user and current_user.get('id') != user['id']:
                    if st.button("🗑️ Excluir Usuário", key=f"delete_detail_{user['id']}", use_container_width=True):
                        # Verificar se tem dados associados
                        if len(reqs) > 0 or len(laudos) > 0:
                            st.warning(
                                f"⚠️ Este usuário possui {len(reqs)} requisição(ões) e {len(laudos)} laudo(s).")
                            st.info(
                                "💡 Considere desativar o usuário em vez de excluí-lo para preservar o histórico.")
                        else:
                            if st.session_state.get(f"confirm_delete_detail_{user['id']}", False):
                                if user_model.delete(user['id']):
                                    del st.session_state['viewing_user']
                                    st.success("✅ Usuário excluído com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("❌ Erro ao excluir usuário")
                            else:
                                st.session_state[f"confirm_delete_detail_{user['id']}"] = True
                                st.warning("⚠️ Clique novamente em 'Excluir Usuário' para confirmar")
                                st.rerun()

            with col_act3:
                if st.button("🔄 Recarregar", key="reload_user_details", use_container_width=True):
                    st.rerun()

            st.divider()
            # Formulário de edição do usuário
            with st.expander("✏️ Editar usuário", expanded=True):
                clinicas_edit = clinica_model.get_all(apenas_ativas=False)
                with st.form("form_editar_usuario"):
                    nome_edit = st.text_input(
                        "Nome Completo *", value=user.get("nome") or "", key="edit_nome")
                    username_edit = st.text_input(
                        "Usuário (login) *", value=user.get("username") or "", key="edit_username")
                    email_edit = st.text_input(
                        "E-mail *", value=user.get("email") or "", key="edit_email")
                    role_edit = st.selectbox(
                        "Tipo de Usuário",
                        ["user", "admin"],
                        index=0 if user.get("role") == "user" else 1,
                        key="edit_role",
                        help="'user' para clientes, 'admin' para administradores",
                    )
                    ativo_edit = st.checkbox("Usuário Ativo", value=user.get(
                        "ativo", True), key="edit_ativo")
                    clinica_options = [None] + [c["id"] for c in clinicas_edit]
                    current_clinica_id = user.get("clinica_id")
                    idx_clinica = 0
                    if current_clinica_id and clinicas_edit:
                        for i, c in enumerate(clinicas_edit):
                            if c["id"] == current_clinica_id:
                                idx_clinica = i + 1
                                break
                    clinica_edit = st.selectbox(
                        "Clínica (para usuário cliente)",
                        options=clinica_options,
                        format_func=lambda x: "— Nenhuma —" if x is None else next(
                            (c["nome"] for c in clinicas_edit if c["id"] == x), x),
                        index=min(idx_clinica, len(clinica_options) - 1) if clinica_options else 0,
                        key="edit_clinica",
                        help="Vínculo do usuário com a clínica. Apenas para tipo 'Cliente'.",
                    )
                    submit_edit = st.form_submit_button("💾 Salvar alterações")
                    if submit_edit:
                        if not nome_edit or not username_edit or not email_edit:
                            st.error("Preencha Nome, Usuário (login) e E-mail.")
                        else:
                            # Verificar se username/email já existem em outro usuário (excluindo o atual)
                            other_by_username = user_model.find_by_username(username_edit.strip())
                            other_by_email = user_model.find_by_email(email_edit.strip())
                            if other_by_username and other_by_username.get("id") != user["id"]:
                                st.error(
                                    f"Usuário '{username_edit.strip()}' já está em uso por outro usuário.")
                            elif other_by_email and other_by_email.get("id") != user["id"]:
                                st.error(
                                    f"E-mail '{email_edit.strip()}' já está cadastrado para outro usuário.")
                            else:
                                try:
                                    updates = {
                                        "nome": nome_edit.strip(),
                                        "username": username_edit.strip(),
                                        "email": email_edit.strip(),
                                        "role": role_edit,
                                        "ativo": ativo_edit,
                                        "clinica_id": clinica_edit if role_edit == "user" else None,
                                    }
                                    if user_model.update(user["id"], updates):
                                        st.success("Usuário atualizado com sucesso!")
                                        st.rerun()
                                    else:
                                        st.warning("Nenhuma alteração foi aplicada.")
                                except Exception as e:
                                    st.error(f"Erro ao atualizar: {str(e)}")
        else:
            st.error("Usuário não encontrado")
            del st.session_state['viewing_user']
            st.rerun()

    else:
        # Feedback de cadastro de usuário
        if st.session_state.get('user_created') and st.session_state.get('new_user_credentials'):
            creds = st.session_state['new_user_credentials']
            st.success("✅ Usuário cadastrado! Compartilhe as credenciais abaixo.")
            st.warning("⚠️ Senha temporária: o usuário será obrigado a alterar no primeiro acesso.")
            st.code(
                f"Usuário: {creds['username']}\nE-mail: {creds['email']}\nSenha temporária: {creds['senha_temporaria']}", language="")
            if st.button("✖️ Fechar", key="close_user_feedback"):
                del st.session_state['user_created']
                del st.session_state['new_user_credentials']
                st.rerun()
            st.divider()

        # Limpar formulário de clínica quando solicitado (antes de renderizar widgets)
        if st.session_state.pop("_clear_nova_clinica_form", False):
            keys_to_clear = [k for k in list(st.session_state.keys())
                             if k.startswith("nova_clinica_")]
            for k in keys_to_clear:
                st.session_state.pop(k, None)
            st.rerun()

        # Mensagem de sucesso ao cadastrar clínica (login e senha para copiar)
        if st.session_state.get("clinica_cadastrada_credenciais"):
            creds = st.session_state["clinica_cadastrada_credenciais"]
            st.success("✅ Clínica e conta de acesso criadas com sucesso!")
            st.info("📋 **Copie as credenciais abaixo e envie ao usuário:**")
            st.code(
                f"Usuário (login): {creds['username']}\nE-mail: {creds['email']}\nSenha temporária: {creds['senha_temporaria']}\n\n⚠️ O usuário será obrigado a alterar a senha no primeiro acesso.",
                language="",
            )
            if st.button("✖️ Fechar", key="close_clinica_feedback"):
                del st.session_state["clinica_cadastrada_credenciais"]
                st.rerun()
            st.divider()

        # 1. Cadastrar nova clínica + conta de acesso (login e senha temporária)
        clinicas_opcoes = clinica_model.get_all(apenas_ativas=True)
        with st.expander("➕ Cadastrar nova clínica", expanded=(len(clinicas_opcoes) == 0)):
            st.caption("Ao cadastrar a clínica, crie também a conta de acesso (uma por clínica). A clínica fará login com esse usuário e verá um dropdown de veterinários nas requisições.")
            # ViaCEP: CEP + Buscar (primeiro na seção de endereço, fora do form)
            prefill = st.session_state.get("nova_clinica_cep_prefill") or {}
            st.markdown("**Endereço**")
            col_cep, col_btn = st.columns([3, 1])
            with col_cep:
                cep_default = prefill.get("cep", "") if prefill else ""
                cep_lookup = st.text_input(
                    "CEP *",
                    value=cep_default,
                    key="nova_clinica_cep_lookup",
                    placeholder="Digite o CEP (com ou sem hífen) e clique em Buscar",
                    help="Ex: 01310-100 ou 01310100",
                )
            with col_btn:
                buscar_cep_btn = st.button(
                    "🔍 Buscar endereço", key="nova_clinica_buscar_cep", type="primary")
            cep_para_buscar = (cep_lookup or "").strip()
            if buscar_cep_btn and cep_para_buscar:
                from utils.viacep import buscar_cep
                data = buscar_cep(cep_para_buscar)
                if data:
                    st.session_state["nova_clinica_cep_prefill"] = data
                    # Preencher campos do form apenas ao receber novos dados (evita conflito com state)
                    st.session_state["nova_clinica_endereco"] = data.get("logradouro", "")
                    st.session_state["nova_clinica_bairro"] = data.get("bairro", "")
                    st.session_state["nova_clinica_cidade"] = data.get("cidade", "")
                    st.session_state["nova_clinica_cep"] = data.get("cep", "")
                    st.success("Endereço encontrado! Os campos abaixo foram preenchidos.")
                    st.rerun()
                else:
                    st.error("CEP não encontrado. Verifique e tente novamente.")

            with st.form("nova_clinica_inline"):
                nome_clinica = st.text_input("Nome da clínica *", key="nova_clinica_nome")
                cnpj_clinica = st.text_input("CNPJ", key="nova_clinica_cnpj")
                endereco_clinica = st.text_input("Logradouro (Rua)", value=prefill.get(
                    "logradouro", ""), key="nova_clinica_endereco", placeholder="Preencha o CEP acima ou digite manualmente")
                col_num, col_bairro = st.columns(2)
                with col_num:
                    numero_clinica = st.text_input(
                        "Número", key="nova_clinica_numero", placeholder="nº")
                with col_bairro:
                    bairro_clinica = st.text_input("Bairro", value=prefill.get(
                        "bairro", ""), key="nova_clinica_bairro")
                col_cidade, col_cep_f = st.columns(2)
                with col_cidade:
                    cidade_clinica = st.text_input("Cidade", value=prefill.get(
                        "cidade", ""), key="nova_clinica_cidade")
                with col_cep_f:
                    cep_clinica = st.text_input("CEP", value=prefill.get(
                        "cep", ""), key="nova_clinica_cep", placeholder="00000-000")
                telefone_clinica = st.text_input("Telefone", key="nova_clinica_telefone")
                email_clinica = st.text_input(
                    "E-mail *", key="nova_clinica_email",
                    help="E-mail da clínica e da conta de acesso (login)")
                username_clinica = st.text_input(
                    "Usuário para login *", key="nova_clinica_username")

                if st.form_submit_button("Salvar clínica e conta de acesso"):
                    if not nome_clinica or not nome_clinica.strip():
                        st.error("Preencha o nome da clínica.")
                    elif not username_clinica or not username_clinica.strip():
                        st.error("Preencha o usuário para login.")
                    elif not email_clinica or not email_clinica.strip():
                        st.error("Preencha o e-mail.")
                    elif user_model.find_by_username(username_clinica.strip()):
                        st.error("Este usuário já está em uso.")
                    elif user_model.find_by_email(email_clinica.strip()):
                        st.error("Este e-mail já está cadastrado.")
                    else:
                        try:
                            import secrets
                            import string
                            from auth.auth_utils import hash_password
                            clinica_id_inline = clinica_model.create(
                                nome=nome_clinica.strip(),
                                cnpj=cnpj_clinica or "",
                                endereco=endereco_clinica or "",
                                numero=numero_clinica or "",
                                bairro=bairro_clinica or "",
                                cidade=cidade_clinica or "",
                                cep=cep_clinica or "",
                                telefone=telefone_clinica or "",
                                email=email_clinica.strip() or "",
                                ativa=True,
                            )
                            alphabet = string.ascii_letters + string.digits
                            senha_tmp = ''.join(secrets.choice(alphabet) for _ in range(8))
                            user_model.create(
                                username=username_clinica.strip(),
                                email=email_clinica.strip(),
                                password_hash=hash_password(senha_tmp),
                                role="user",
                                nome=nome_clinica.strip(),
                                ativo=True,
                                primeiro_acesso=True,
                                senha_temporaria=senha_tmp,
                                clinica_id=clinica_id_inline,
                            )
                            st.session_state["clinica_cadastrada_credenciais"] = {
                                "username": username_clinica.strip(),
                                "email": email_clinica.strip(),
                                "senha_temporaria": senha_tmp,
                                "nome_clinica": nome_clinica.strip(),
                            }
                            st.session_state["_clear_nova_clinica_form"] = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {str(e)}")

        # 2. Clientes (cada clínica = conta de acesso + veterinários)
        st.subheader("Clientes")
        clinicas_list = clinica_model.get_all(apenas_ativas=False)
        edit_key = st.session_state.get("clinica_edit_id")
        all_users = user_model.get_all()
        for clin in clinicas_list:
            with st.expander(f"🏥 {clin.get('nome', '—')} {' (inativa)' if not clin.get('ativa', True) else ''}", expanded=(edit_key == clin["id"])):
                if edit_key == clin["id"]:
                    # ViaCEP para edição
                    edit_prefill_key = f"clinica_cep_edit_{clin['id']}"
                    edit_prefill = st.session_state.get(edit_prefill_key) or {}
                    col_ec, col_eb = st.columns([3, 1])
                    with col_ec:
                        cep_edit = st.text_input("CEP (buscar endereço)", value=edit_prefill.get(
                            "cep", clin.get("cep", "")), key=f"clinica_cep_lookup_{clin['id']}", placeholder="00000-000")
                    with col_eb:
                        buscar_edit = st.button("🔍 Buscar", key=f"clinica_buscar_cep_{clin['id']}")
                    if buscar_edit and cep_edit:
                        from utils.viacep import buscar_cep
                        data = buscar_cep(cep_edit)
                        if data:
                            st.session_state[edit_prefill_key] = data
                            st.success("Endereço encontrado!")
                            st.rerun()
                        else:
                            st.error("CEP não encontrado.")
                    with st.form(f"form_clinica_edit_{clin['id']}"):
                        nome_c = st.text_input(
                            "Nome *", value=clin.get("nome", ""), key=f"clinica_nome_{clin['id']}")
                        cnpj_c = st.text_input("CNPJ", value=clin.get(
                            "cnpj", ""), key=f"clinica_cnpj_{clin['id']}")
                        st.markdown("**Endereço**")
                        endereco_c = st.text_input("Logradouro (Rua)", value=edit_prefill.get(
                            "logradouro", clin.get("endereco", "")), key=f"clinica_endereco_{clin['id']}")
                        col_nc, col_bc = st.columns(2)
                        with col_nc:
                            numero_c = st.text_input("Número", value=clin.get(
                                "numero", ""), key=f"clinica_numero_{clin['id']}")
                        with col_bc:
                            bairro_c = st.text_input("Bairro", value=edit_prefill.get(
                                "bairro", clin.get("bairro", "")), key=f"clinica_bairro_{clin['id']}")
                        col_cc, col_cec = st.columns(2)
                        with col_cc:
                            cidade_c = st.text_input("Cidade", value=edit_prefill.get(
                                "cidade", clin.get("cidade", "")), key=f"clinica_cidade_{clin['id']}")
                        with col_cec:
                            cep_c = st.text_input("CEP", value=edit_prefill.get(
                                "cep", clin.get("cep", "")), key=f"clinica_cep_{clin['id']}")
                        telefone_c = st.text_input("Telefone", value=clin.get(
                            "telefone", ""), key=f"clinica_telefone_{clin['id']}")
                        email_c = st.text_input(
                            "E-mail", value=clin.get("email", ""), key=f"clinica_email_{clin['id']}")
                        ativa_c = st.checkbox("Ativa", value=clin.get(
                            "ativa", True), key=f"clinica_ativa_{clin['id']}")
                        if st.form_submit_button("Salvar"):
                            clinica_model.update(clin["id"], {
                                "nome": nome_c.strip(), "cnpj": cnpj_c or "",
                                "endereco": endereco_c or "", "numero": numero_c or "", "bairro": bairro_c or "",
                                "cidade": cidade_c or "", "cep": cep_c or "",
                                "telefone": telefone_c or "", "email": email_c or "", "ativa": ativa_c
                            })
                            if edit_prefill_key in st.session_state:
                                del st.session_state[edit_prefill_key]
                            del st.session_state["clinica_edit_id"]
                            st.success("Clínica atualizada.")
                            st.rerun()
                    if st.button("Cancelar edição", key=f"cancel_edit_{clin['id']}"):
                        del st.session_state["clinica_edit_id"]
                        if f"clinica_cep_edit_{clin['id']}" in st.session_state:
                            del st.session_state[f"clinica_cep_edit_{clin['id']}"]
                        st.rerun()
                else:
                    row_edit, row_del, row_excluir, row_info = st.columns([1, 1, 1, 11])
                    with row_edit:
                        if st.button("✏️", key=f"edit_clin_{clin['id']}", help="Editar clínica"):
                            st.session_state["clinica_edit_id"] = clin["id"]
                            st.rerun()
                    with row_del:
                        if clin.get("ativa", True):
                            if st.button("🚫", key=f"desativar_clin_{clin['id']}", help="Desativar clínica"):
                                clinica_model.update(clin["id"], {"ativa": False})
                                st.rerun()
                        else:
                            if st.button("✅", key=f"ativar_clin_{clin['id']}", help="Ativar clínica"):
                                clinica_model.update(clin["id"], {"ativa": True})
                                st.rerun()
                    with row_excluir:
                        delete_clin_key = f"excluir_clin_{clin['id']}"
                        if st.button("🗑️", key=delete_clin_key, help="Excluir clínica"):
                            if not st.session_state.get(f"confirm_{delete_clin_key}", False):
                                st.session_state[f"confirm_{delete_clin_key}"] = True
                                st.warning(
                                    f"⚠️ Clique novamente em 🗑️ para confirmar a exclusão de '{clin.get('nome', '—')}'")
                                st.rerun()
                            else:
                                if clinica_model.delete(clin["id"]):
                                    del st.session_state[f"confirm_{delete_clin_key}"]
                                    st.success("Clínica excluída.")
                                    st.rerun()
                                else:
                                    st.error("Erro ao excluir clínica")
                                    del st.session_state[f"confirm_{delete_clin_key}"]
                    with row_info:
                        st.write(
                            f"**{clin.get('nome', '—')}** {' _(inativa)_' if not clin.get('ativa', True) else ''}")
                        end = clin.get('endereco') or ''
                        num = clin.get('numero', '')
                        bair = clin.get('bairro', '')
                        cid = clin.get('cidade', '')
                        cp = clin.get('cep', '')
                        addr = ", ".join(x for x in [end, num, bair, cid, cp] if x)
                        st.caption(
                            f"CNPJ: {clin.get('cnpj') or '—'} · Endereço: {addr or '—'} · Tel: {clin.get('telefone') or '—'} · {clin.get('email') or '—'}")

                # Conta de acesso (login da clínica)
                user_clinica = next(
                    (u for u in all_users if u.get("clinica_id") == clin["id"]), None)
                if user_clinica:
                    st.markdown("**Conta de acesso**")
                    senha_info = f" · Senha temporária: `{user_clinica.get('senha_temporaria', '—')}`" if user_clinica.get(
                        "primeiro_acesso") else ""
                    st.caption(
                        f"Login: `{user_clinica.get('username', '—')}` · E-mail: `{user_clinica.get('email', '—')}`{senha_info}")

                st.markdown("**Veterinários**")
                veterinarios_list = veterinario_model.find_by_clinica(
                    clin["id"], apenas_ativos=False)
                if st.button("➕ Adicionar Veterinário", key=f"add_vet_{clin['id']}"):
                    st.session_state[f"vet_add_{clin['id']}"] = True
                    st.rerun()
                if st.session_state.get(f"vet_add_{clin['id']}"):
                    with st.form(f"form_vet_new_{clin['id']}"):
                        nome_v = st.text_input("Nome *", key=f"vet_nome_{clin['id']}_new")
                        crmv_v = st.text_input("CRMV *", key=f"vet_crmv_{clin['id']}_new")
                        email_v = st.text_input("E-mail", key=f"vet_email_{clin['id']}_new")
                        if st.form_submit_button("Salvar"):
                            if nome_v and nome_v.strip() and crmv_v and crmv_v.strip():
                                veterinario_model.create(nome=nome_v.strip(), crmv=crmv_v.strip(
                                ), clinica_id=clin["id"], email=email_v or "")
                                del st.session_state[f"vet_add_{clin['id']}"]
                                st.success("Veterinário cadastrado.")
                                st.rerun()
                            else:
                                st.error("Preencha nome e CRMV.")
                    if st.button("Cancelar", key=f"vet_cancel_{clin['id']}"):
                        del st.session_state[f"vet_add_{clin['id']}"]
                        st.rerun()
                for vet in veterinarios_list:
                    ve, vr, vt = st.columns([1, 1, 12])
                    with ve:
                        if st.button("✏️", key=f"edit_vet_{vet['id']}", help="Editar"):
                            st.session_state[f"vet_edit_{vet['id']}"] = True
                            st.rerun()
                    with vr:
                        if st.button("🗑️", key=f"remover_vet_{vet['id']}", help="Remover"):
                            veterinario_model.delete(vet["id"])
                            st.rerun()
                    with vt:
                        st.write(
                            f"• **{vet.get('nome', '—')}** — CRMV: {vet.get('crmv', '—')} {' _(inativo)_' if not vet.get('ativo', True) else ''}")
                    if st.session_state.get(f"vet_edit_{vet['id']}"):
                        with st.form(f"form_vet_edit_{vet['id']}"):
                            nome_v = st.text_input(
                                "Nome *", value=vet.get("nome", ""), key=f"vet_nome_edit_{vet['id']}")
                            crmv_v = st.text_input(
                                "CRMV *", value=vet.get("crmv", ""), key=f"vet_crmv_edit_{vet['id']}")
                            email_v = st.text_input(
                                "E-mail", value=vet.get("email", ""), key=f"vet_email_edit_{vet['id']}")
                            ativo_v = st.checkbox("Ativo", value=vet.get(
                                "ativo", True), key=f"vet_ativo_edit_{vet['id']}")
                            if st.form_submit_button("Salvar"):
                                veterinario_model.update(vet["id"], {"nome": nome_v.strip(
                                ), "crmv": crmv_v.strip(), "email": email_v or "", "ativo": ativo_v})
                                del st.session_state[f"vet_edit_{vet['id']}"]
                                st.success("Veterinário atualizado.")
                                st.rerun()

        # 3. Administradores (apenas admins; clientes são gerenciados via clínicas acima)
        admins = [u for u in user_model.get_all(role="admin") if u.get('clinica_id') is None]
        admins = [u for u in admins if u.get('ativo', True)] + \
            [u for u in admins if not u.get('ativo', True)]

        if admins:
            st.subheader("👨‍⚕️ Administradores")
            for user in admins:
                status_badge = "✅ Ativo" if user.get('ativo', True) else "🚫 Inativo"
                with st.expander(f"👨‍⚕️ {user.get('nome', user.get('username'))} · {status_badge}", expanded=False):
                    st.caption(f"Login: `{user.get('username')}` · E-mail: `{user.get('email')}`")
                    reqs = requisicao_model.find_by_user(user['id'])
                    laudos = laudo_model.find_by_user(user['id'])
                    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                    with col_btn1:
                        if user.get('ativo'):
                            if st.button("🚫 Desativar", key=f"deactivate_{user['id']}", use_container_width=True):
                                user_model.update(user['id'], {"ativo": False})
                                st.success("Usuário desativado")
                                st.rerun()
                        else:
                            if st.button("✅ Ativar", key=f"activate_{user['id']}", use_container_width=True):
                                user_model.update(user['id'], {"ativo": True})
                                st.success("Usuário ativado")
                                st.rerun()

                    with col_btn2:
                        if st.button("📊 Ver Detalhes", key=f"details_{user['id']}", use_container_width=True):
                            st.session_state['viewing_user'] = user['id']
                            st.rerun()

                    with col_btn3:
                        if st.button("✏️ Editar", key=f"edit_btn_{user['id']}", use_container_width=True):
                            st.session_state['viewing_user'] = user['id']
                            st.rerun()

                    with col_btn4:
                        # Não permitir excluir o próprio usuário
                        current_user = get_current_user()
                        if current_user and current_user.get('id') == user['id']:
                            st.button("🗑️ Excluir", key=f"delete_{user['id']}", disabled=True, use_container_width=True,
                                      help="Você não pode excluir seu próprio usuário")
                        else:
                            # Verificar se é o admin dummy
                            is_dummy = user.get('username') == 'admin' and user.get(
                                'email') == 'admin@paics.local'

                            has_data = len(reqs) > 0 or len(laudos) > 0
                            delete_key = f"delete_{user['id']}"
                            if st.button("🗑️ Excluir", key=delete_key, use_container_width=True):
                                if not st.session_state.get(f"confirm_{delete_key}", False):
                                    st.session_state[f"confirm_{delete_key}"] = True
                                    st.warning(
                                        f"⚠️ Clique novamente em 'Excluir' para confirmar a exclusão de '{user.get('username')}'")
                                    if has_data:
                                        st.info(
                                            "💡 O usuário possui requisições/laudos. Eles permanecerão no sistema com referência ao usuário excluído. Considere desativar em vez de excluir.")
                                    if is_dummy:
                                        st.info(
                                            "💡 Certifique-se de ter criado seu próprio usuário administrador antes de excluir o dummy.")
                                    st.rerun()
                                else:
                                    if user_model.delete(user['id']):
                                        del st.session_state[f"confirm_{delete_key}"]
                                        if is_dummy:
                                            st.success("✅ Usuário dummy excluído com sucesso!")
                                        else:
                                            st.success("✅ Usuário excluído com sucesso!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Erro ao excluir usuário")
                                        del st.session_state[f"confirm_{delete_key}"]

elif page == "Financeiro":
    st.header("💰 Painel Financeiro")

    tab1, tab2 = st.tabs(["Gerar Fechamento", "Faturas"])

    with tab1:
        st.subheader("📊 Gerar Fechamento de Exames")

        col1, col2, col3 = st.columns(3)
        with col1:
            data_inicio = st.date_input("Data Início", value=now().replace(day=1).date())
        with col2:
            data_fim = st.date_input("Data Fim", value=now().date())
        with col3:
            valor_exame = st.number_input("Valor por Exame (R$)",
                                          min_value=0.0, value=35.0, step=1.0)
            valor_plantao = st.number_input(
                "Acréscimo Plantão (R$)",
                min_value=0.0,
                value=60.0,
                step=1.0,
                help="Valor adicional cobrado para exames em regime de plantão.",
            )

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("📊 Gerar Fechamento (Todos Usuários)", use_container_width=True):
                from utils.financeiro import (
                    gerar_fechamento_todos_usuarios,
                    criar_fatura,
                    set_valor_base_exame,
                    set_acrescimo_plantao,
                )

                try:
                    # Atualizar configurações padrões (com histórico)
                    current_admin = get_current_user()
                    admin_name = current_admin.get("username") if current_admin else None
                    set_valor_base_exame(valor_exame, changed_by=admin_name)
                    set_acrescimo_plantao(valor_plantao, changed_by=admin_name)

                    fechamentos = gerar_fechamento_todos_usuarios(
                        get_date_start(combine_date_local(data_inicio)),
                        get_date_end(combine_date_local(data_fim)),
                        valor_por_exame=valor_exame,
                        valor_plantao=valor_plantao,
                    )

                    if fechamentos:
                        st.success(f"✅ {len(fechamentos)} fechamento(s) gerado(s)!")

                        # Criar faturas
                        faturas_criadas = []
                        for item in fechamentos:
                            fatura_id = criar_fatura(
                                item['usuario']['id'],
                                item['fechamento']['periodo'],
                                item['fechamento']['exames'],
                                item['fechamento']['valor_total']
                            )
                            faturas_criadas.append({
                                'usuario': item['usuario'],
                                'fatura_id': fatura_id,
                                'fechamento': item['fechamento']
                            })

                        # Mostrar resumo
                        st.subheader("📋 Resumo dos Fechamentos")
                        total_geral = sum(f['fechamento']['valor_total'] for f in faturas_criadas)
                        st.metric("Total Geral", f"R$ {total_geral:.2f}")

                        for item in faturas_criadas:
                            with st.expander(f"👤 {item['usuario'].get('nome', item['usuario'].get('username'))} - R$ {item['fechamento']['valor_total']:.2f}"):
                                st.write(f"**Período:** {item['fechamento']['periodo']}")
                                st.write(
                                    f"**Quantidade de Exames:** {item['fechamento']['quantidade_exames']}")
                                st.write(
                                    f"**Valor Total:** R$ {item['fechamento']['valor_total']:.2f}")
                                st.write(f"**Fatura ID:** {item['fatura_id'][:8]}")
                    else:
                        st.info("Nenhum exame encontrado no período especificado.")
                except Exception as e:
                    st.error(f"Erro ao gerar fechamento: {str(e)}")

        with col_btn2:
            # Fechamento para usuário específico
            usuarios = user_model.get_all(role="user")
            usuario_selecionado = st.selectbox(
                "Selecionar Usuário",
                [None]
                + [f"{u.get('nome', u.get('username'))} ({u.get('email')})" for u in usuarios],
                key="user_fechamento"
            )

            if usuario_selecionado and st.button("📊 Gerar Fechamento (Usuário)", use_container_width=True):
                from utils.financeiro import (
                    gerar_fechamento,
                    criar_fatura,
                    set_valor_base_exame,
                    set_acrescimo_plantao,
                )

                # Extrair user_id do selecionado
                user_idx = usuarios.index(
                    [u for u in usuarios if f"{u.get('nome', u.get('username'))} ({u.get('email')})" == usuario_selecionado][0])
                user_selected = usuarios[user_idx]

                try:
                    # Atualizar configurações padrões (com histórico)
                    current_admin = get_current_user()
                    admin_name = current_admin.get("username") if current_admin else None
                    set_valor_base_exame(valor_exame, changed_by=admin_name)
                    set_acrescimo_plantao(valor_plantao, changed_by=admin_name)

                    fechamento = gerar_fechamento(
                        user_selected['id'],
                        get_date_start(combine_date_local(data_inicio)),
                        get_date_end(combine_date_local(data_fim)),
                        valor_por_exame=valor_exame,
                        valor_plantao=valor_plantao,
                    )

                    if fechamento['quantidade_exames'] > 0:
                        fatura_id = criar_fatura(
                            fechamento['user_id'],
                            fechamento['periodo'],
                            fechamento['exames'],
                            fechamento['valor_total']
                        )

                        st.success(f"✅ Fechamento gerado! Fatura ID: {fatura_id[:8]}")
                        st.json(fechamento)
                    else:
                        st.info("Nenhum exame encontrado para este usuário no período.")
                except Exception as e:
                    st.error(f"Erro: {str(e)}")

    with tab2:
        st.subheader("📋 Faturas")

        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            periodo_filter = st.text_input("🔍 Filtrar por Período (opcional)")
        with col2:
            status_filter = st.selectbox(
                "Filtrar por Status",
                ["Todos", "pendente", "paga", "cancelada"]
            )
        with col3:
            tipo_atendimento_filter = st.selectbox(
                "Tipo de atendimento",
                ["Todos", "Normal", "Plantão"],
                help="Filtra faturas que possuem apenas exames normais ou em plantão.",
            )

        # Buscar faturas
        status = None if status_filter == "Todos" else status_filter
        faturas = fatura_model.find_all(status=status)

        if periodo_filter:
            faturas = [f for f in faturas if periodo_filter in f.get('periodo', '')]

        # Filtrar por tipo de atendimento (normal/plantão)
        if tipo_atendimento_filter != "Todos":
            so_plantao = (tipo_atendimento_filter == "Plantão")
            filtradas = []
            for f in faturas:
                exames = f.get("exames", [])
                if not exames:
                    continue
                has_plantao = any(e.get("plantao") for e in exames)
                if so_plantao and has_plantao:
                    filtradas.append(f)
                if not so_plantao and not has_plantao:
                    filtradas.append(f)
            faturas = filtradas

        st.metric("Total de Faturas", len(faturas))
        total_pendente = sum(f.get('valor_total', 0)
                             for f in faturas if f.get('status') == 'pendente')
        st.metric("Total Pendente", f"R$ {total_pendente:.2f}")

        # Lista de faturas
        for fatura in faturas:
            user = user_model.find_by_id(fatura.get('user_id'))
            status_badge = {
                "pendente": "⏳ Pendente",
                "paga": "✅ Paga",
                "cancelada": "❌ Cancelada"
            }.get(fatura.get('status'), fatura.get('status'))

            with st.expander(f"💰 {user.get('nome', user.get('username')) if user else 'N/A'} - {fatura.get('periodo')} - R$ {fatura.get('valor_total', 0):.2f} - {status_badge}"):
                col1, col2 = st.columns(2)

                with col1:
                    if user:
                        st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
                        st.write(f"**E-mail:** {user.get('email')}")
                    st.write(f"**Período:** {fatura.get('periodo')}")
                    st.write(f"**Valor Total:** R$ {fatura.get('valor_total', 0):.2f}")
                    st.write(f"**Status:** {fatura.get('status')}")
                    st.write(f"**Criada em:** {fatura.get('created_at')}")

                with col2:
                    st.write(f"**Quantidade de Exames:** {len(fatura.get('exames', []))}")

                    # Lista de exames com breakdown de valores
                    if fatura.get('exames'):
                        st.write("**Exames:**")
                        for exame in fatura.get('exames', [])[:10]:  # Mostrar até 10
                            valor_base = exame.get('valor_base', exame.get('valor', 0))
                            acrescimo_plantao = exame.get('acrescimo_plantao', 0.0)
                            valor_total_exame = exame.get('valor', valor_base + acrescimo_plantao)
                            plantao_flag = exame.get('plantao', False)
                            obs = exame.get('observacao', '')
                            linha = f"- {exame.get('paciente', 'N/A')} ({exame.get('tipo_exame', 'N/A')})"
                            linha += f" · Base: R$ {valor_base:.2f}"
                            if plantao_flag and acrescimo_plantao:
                                linha += f" · Plantão: +R$ {acrescimo_plantao:.2f}"
                            linha += f" · Total: R$ {valor_total_exame:.2f}"
                            if obs:
                                linha += f" · Obs: {obs}"
                            st.write(linha)
                        if len(fatura.get('exames', [])) > 10:
                            st.write(f"... e mais {len(fatura.get('exames', [])) - 10} exame(s)")

                    # Ações
                    if fatura.get('status') == 'pendente':
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅ Marcar como Paga", key=f"pay_{fatura['id']}"):
                                fatura_model.update_status(fatura['id'], 'paga')
                                st.success("Fatura marcada como paga")
                                st.rerun()
                        with col_btn2:
                            if st.button("❌ Cancelar", key=f"cancel_{fatura['id']}"):
                                fatura_model.update_status(fatura['id'], 'cancelada')
                                st.success("Fatura cancelada")
                                st.rerun()

elif page == "Knowledge Base e Aprendizado":
    st.header("📚 Knowledge Base e Aprendizado")

    tab_kb, tab_aprend = st.tabs(
        ["Conteúdo (PDFs, Prompts, Orientações)", "Sistema de Aprendizado"])

    with tab_kb:
        st.info("Gerencie PDFs, prompts e orientações para o modelo local")

        from knowledge_base.kb_manager import KnowledgeBaseManager

        kb_manager = KnowledgeBaseManager()

        tab1, tab2, tab3 = st.tabs(["Adicionar Conteúdo", "Buscar", "Listar Tudo"])

        with tab1:
            st.subheader("Adicionar Novo Conteúdo")

            tipo_conteudo = st.selectbox("Tipo de Conteúdo", ["PDF", "Prompt", "Orientação"])

            if tipo_conteudo == "PDF":
                uploaded_file = st.file_uploader("Selecionar PDF", type=['pdf'])
                titulo = st.text_input("Título")
                tags_input = st.text_input("Tags (separadas por vírgula)")

                if st.button("📤 Adicionar PDF"):
                    if uploaded_file and titulo:
                        try:
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                tmp_file.write(uploaded_file.getbuffer())
                                tmp_path = tmp_file.name

                            tags = [t.strip() for t in tags_input.split(
                                ',') if t.strip()] if tags_input else []
                            kb_id = kb_manager.add_pdf(tmp_path, titulo, tags)
                            st.success(f"✅ PDF adicionado com sucesso! ID: {kb_id[:8]}")

                            os.unlink(tmp_path)
                        except Exception as e:
                            st.error(f"Erro ao adicionar PDF: {str(e)}")

            elif tipo_conteudo == "Prompt":
                titulo = st.text_input("Título")
                conteudo = st.text_area("Conteúdo do Prompt", height=200)
                tags_input = st.text_input("Tags (separadas por vírgula)")

                if st.button("📤 Adicionar Prompt"):
                    if titulo and conteudo:
                        try:
                            tags = [t.strip() for t in tags_input.split(
                                ',') if t.strip()] if tags_input else []
                            kb_id = kb_manager.add_prompt(titulo, conteudo, tags)
                            st.success(f"✅ Prompt adicionado com sucesso! ID: {kb_id[:8]}")
                        except Exception as e:
                            st.error(f"Erro ao adicionar prompt: {str(e)}")

            elif tipo_conteudo == "Orientação":
                titulo = st.text_input("Título")
                conteudo = st.text_area("Conteúdo da Orientação", height=200)
                tags_input = st.text_input("Tags (separadas por vírgula)")

                if st.button("📤 Adicionar Orientação"):
                    if titulo and conteudo:
                        try:
                            tags = [t.strip() for t in tags_input.split(
                                ',') if t.strip()] if tags_input else []
                            kb_id = kb_manager.add_orientacao(titulo, conteudo, tags)
                            st.success(f"✅ Orientação adicionada com sucesso! ID: {kb_id[:8]}")
                        except Exception as e:
                            st.error(f"Erro ao adicionar orientação: {str(e)}")

        with tab2:
            st.subheader("🔍 Buscar na Knowledge Base")

            query = st.text_input("Digite sua busca")
            n_results = st.slider("Número de resultados", 1, 20, 5)

            if st.button("🔍 Buscar") and query:
                try:
                    results = kb_manager.search(query, n_results)

                    if results:
                        st.success(f"Encontrados {len(results)} resultado(s)")

                        for idx, result in enumerate(results, 1):
                            kb_item = result['kb_item']
                            with st.expander(f"#{idx} - {kb_item.get('titulo')} (Relevância: {result['relevancia']:.2%})"):
                                st.write(f"**Tipo:** {kb_item.get('tipo')}")
                                st.write(f"**Tags:** {', '.join(kb_item.get('tags', []))}")
                                st.write(f"**Relevância:** {result['relevancia']:.2%}")
                                st.text_area("Conteúdo", value=kb_item.get('conteudo', '')
                                             [:500] + "...", height=150, disabled=True)
                    else:
                        st.info("Nenhum resultado encontrado.")
                except Exception as e:
                    st.error(f"Erro na busca: {str(e)}")

        with tab3:
            st.subheader("📋 Todos os Itens")

            tipo_filter = st.selectbox("Filtrar por Tipo", ["Todos", "pdf", "prompt", "orientacao"])

            tipo = None if tipo_filter == "Todos" else tipo_filter
            items = kb_manager.get_all(tipo=tipo)

            st.metric("Total de Itens", len(items))

            for item in items:
                with st.expander(f"📄 {item.get('titulo')} - {item.get('tipo')}"):
                    st.write(f"**Tipo:** {item.get('tipo')}")
                    st.write(f"**Tags:** {', '.join(item.get('tags', []))}")
                    st.write(f"**Criado em:** {item.get('created_at')}")
                    st.text_area("Conteúdo", value=item.get('conteudo', '')
                                 [:300] + "...", height=100, disabled=True)

    with tab_aprend:
        st.header("🧠 Sistema de Aprendizado Contínuo")

        try:
            from ai.learning_system import LearningSystem
            learning_system = LearningSystem()

            # Obter estatísticas
            stats = learning_system.get_statistics()

            st.info("""
            **Sistema de Aprendizado Contínuo**

            Este sistema aprende com cada laudo processado:
            - **Rating 5/5**: Laudo aprovado sem edições → usado como referência
            - **Rating 3/5**: Laudo editado parcialmente → aprendizado moderado
            - **Rating 1/5**: Laudo muito editado → caso complexo, requer API externa

            O sistema usa casos similares para decidir quando usar modelo local vs API externa.
            """)

            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("📊 Total de Casos", stats.get("total_casos", 0))

            with col2:
                taxa_aprov = stats.get("taxa_aprovacao", 0)
                st.metric("✅ Taxa de Aprovação", f"{taxa_aprov:.1f}%")

            with col3:
                economia = stats.get("economia_api", 0)
                st.metric("💰 Economia API", f"{economia:.1f}%")

            with col4:
                local_only = stats.get("local_only", 0)
                st.metric("🏠 Modelo Local", local_only)

            st.divider()

            # Distribuição de ratings
            st.subheader("📈 Distribuição de Ratings")
            col_r1, col_r2, col_r3 = st.columns(3)

            with col_r1:
                rating_5 = stats.get("rating_5", 0)
                st.metric("⭐ Rating 5/5", rating_5, help="Laudos aprovados sem edições")

            with col_r2:
                rating_3 = stats.get("rating_3", 0)
                st.metric("⭐ Rating 3/5", rating_3, help="Laudos editados parcialmente")

            with col_r3:
                rating_1 = stats.get("rating_1", 0)
                st.metric("⭐ Rating 1/5", rating_1, help="Laudos muito editados")

            # Gráfico de distribuição
            if stats.get("total_casos", 0) > 0:
                try:
                    import pandas as pd
                    import plotly.express as px

                    df_ratings = pd.DataFrame({
                        "Rating": ["5/5", "3/5", "1/5"],
                        "Quantidade": [rating_5, rating_3, rating_1]
                    })

                    fig = px.pie(
                        df_ratings,
                        values="Quantidade",
                        names="Rating",
                        title="Distribuição de Ratings",
                        color="Rating",
                        color_discrete_map={"5/5": "#2e7d32", "3/5": "#f57c00", "1/5": "#d32f2f"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    st.warning("Biblioteca plotly não instalada. Instale com: pip install plotly")
                except Exception as e:
                    st.warning(f"Erro ao gerar gráfico: {str(e)}")

            st.divider()

            # Uso de modelos
            st.subheader("🤖 Uso de Modelos")
            col_m1, col_m2 = st.columns(2)

            with col_m1:
                st.metric("🏠 Apenas Local", stats.get("local_only", 0))

            with col_m2:
                st.metric("🌐 Com API Externa", stats.get("api_used", 0))

            st.divider()

            # Configurações do sistema
            st.subheader("⚙️ Configurações do Sistema")

            col_c1, col_c2, col_c3 = st.columns(3)

            with col_c1:
                threshold = st.number_input(
                    "Threshold de Similaridade",
                    min_value=0.0,
                    max_value=1.0,
                    value=learning_system.similarity_threshold,
                    step=0.05,
                    help="Similaridade mínima para usar apenas modelo local"
                )

            with col_c2:
                min_rating = st.number_input(
                    "Rating Mínimo para Local",
                    min_value=1,
                    max_value=5,
                    value=learning_system.min_rating_for_local,
                    step=1,
                    help="Rating mínimo dos casos similares para usar modelo local"
                )

            with col_c3:
                use_fallback = st.checkbox(
                    "Usar Fallback para API Externa",
                    value=learning_system.use_external_fallback,
                    help="Se modelo local falhar, usar API externa automaticamente"
                )

            if st.button("💾 Salvar Configurações"):
                st.success("Configurações salvas! (Reinicie o sistema para aplicar)")

            st.divider()

            # Últimos casos aprendidos
            st.subheader("📚 Últimos Casos Aprendidos")

            from database.models import LearningHistory
            learning_model = LearningHistory(get_db().learning_history)

            todos_casos = learning_model.collection.find().sort("created_at", -1).limit(10)
            casos_list = [learning_model.to_dict(doc) for doc in todos_casos]

            if casos_list:
                for caso in casos_list:
                    with st.expander(f"📋 Caso {caso.get('id', 'N/A')[:8]} - Rating: {caso.get('rating', 'N/A')}/5"):
                        col_case1, col_case2 = st.columns(2)

                        with col_case1:
                            st.write("**Contexto:**")
                            contexto = caso.get("contexto", {})
                            st.write(f"- Espécie: {contexto.get('especie', 'N/A')}")
                            st.write(f"- Raça: {contexto.get('raca', 'N/A')}")
                            st.write(f"- Região: {contexto.get('regiao_estudo', 'N/A')}")
                            st.write(f"- Suspeita: {contexto.get('suspeita_clinica', 'N/A')}")

                        with col_case2:
                            st.write("**Modelo:**")
                            st.write(f"- Tipo: {caso.get('modelo_usado', 'N/A')}")
                            st.write(
                                f"- API Externa: {'Sim' if caso.get('usado_api_externa') else 'Não'}")
                            st.write(f"- Similaridade: {caso.get('similaridade_casos', 0):.2%}" if caso.get(
                                'similaridade_casos') else "- Similaridade: N/A")
                            st.write(f"- Data: {caso.get('created_at', 'N/A')}")
            else:
                st.info("Nenhum caso aprendido ainda. Os casos serão registrados quando laudos forem liberados.")

        except Exception as e:
            st.error(f"Erro ao carregar métricas: {str(e)}")
            st.exception(e)
