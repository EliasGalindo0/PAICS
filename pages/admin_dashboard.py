"""
Dashboard do Administrador
"""
import time
from auth.auth_utils import verify_and_refresh_session
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from auth.auth_utils import get_current_user, clear_session, require_auth, logout_user
from database.connection import get_db
from database.models import Requisicao, Laudo, User, Fatura
import os
import io
import zipfile
import base64

# IMPORTANTE: Script deve executar ANTES de qualquer verificação Python
# Usar st.markdown para garantir execução na página principal (não em iframe)
# Colocar no início para executar o mais cedo possível
st.markdown("""
    <script>
    // Executar imediatamente quando o script carrega (antes do Python processar)
    (function() {
        function checkAndRedirect() {
            // Verificar se já temos user_id nos query params
            const url = new URL(window.location);
            const currentRestoreId = url.searchParams.get('restore_user_id');
            
            if (currentRestoreId) {
                return; // Não fazer nada, já tem o parâmetro
            }
            
            // Verificar localStorage para user_id (salvo no login)
            const userId = localStorage.getItem('paics_user_id');
            
            if (userId && userId.trim() !== '') {
                // Passar user_id para o Python via query params
                url.searchParams.set('restore_user_id', userId);
                window.location.replace(url.toString());
            }
        }
        
        // Tentar executar imediatamente
        checkAndRedirect();
        
        // Também executar quando o DOM estiver pronto (fallback)
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', checkAndRedirect);
        } else {
            setTimeout(checkAndRedirect, 100);
        }
    })();
    </script>
""", unsafe_allow_html=True)
# PIL.Image será importado lazy quando necessário (evita problemas com Python 3.13)

# IMPORTANTE: st.set_page_config deve vir ANTES do script JavaScript
# Mas o script JavaScript precisa executar o mais cedo possível
st.set_page_config(
    page_title="Dashboard Admin - PAICS",
    page_icon="👨‍⚕️",
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

# Script para verificar localStorage e passar user_id para o Python
# Executar IMEDIATAMENTE quando a página carrega - ANTES de qualquer verificação Python
# Usar runOnLoad para garantir execução antes do Python processar
st.markdown("""
    <script>
    // Executar imediatamente quando o script carrega
    (function() {
        console.log('🚀 [ADMIN-DASH] Script de verificação iniciado');
        
        // Verificar se já temos user_id nos query params
        const url = new URL(window.location);
        const currentRestoreId = url.searchParams.get('restore_user_id');
        console.log('📍 [ADMIN-DASH] URL atual:', url.toString());
        console.log('   restore_user_id atual:', currentRestoreId);
        
        if (currentRestoreId) {
            console.log('⏭️ [ADMIN-DASH] Já tem restore_user_id nos query params:', currentRestoreId);
        } else {
            // Verificar localStorage para user_id (salvo no login)
            const userId = localStorage.getItem('paics_user_id');
            console.log('🔍 [ADMIN-DASH] Verificando localStorage...');
            console.log('   User ID encontrado:', userId);
            const paicsKeys = Object.keys(localStorage).filter(k => k.startsWith('paics'));
            console.log('   Todos os itens do localStorage (paics*):', paicsKeys);
            paicsKeys.forEach(k => {
                console.log(`      ${k}: ${localStorage.getItem(k)?.substring(0, 50)}...`);
            });
            
            if (userId && userId.trim() !== '') {
                console.log('✅ [ADMIN-DASH] User ID encontrado! Adicionando aos query params...');
                // Passar user_id para o Python via query params
                url.searchParams.set('restore_user_id', userId);
                const newUrl = url.toString();
                console.log('🔄 [ADMIN-DASH] Redirecionando para:', newUrl.substring(0, 200));
                // Usar replace para evitar histórico desnecessário e garantir execução imediata
                window.location.replace(newUrl);
            } else {
                console.log('❌ [ADMIN-DASH] User ID não encontrado no localStorage ou está vazio');
            }
        }
    })();
    </script>
""", unsafe_allow_html=True)

# Verificar autenticação e tokens

# Função para carregar tokens do localStorage


def load_tokens_from_localstorage():
    """Carrega tokens do localStorage e coloca no session_state"""
    # Verificar se já temos tokens
    if st.session_state.get('access_token') and st.session_state.get('refresh_token'):
        return

    # Processar tokens da query string primeiro (se vieram do JavaScript)
    query_params = st.query_params
    if query_params.get('auto_login') == 'true':
        access_token_b64 = query_params.get('access_token', [''])[0]
        refresh_token_b64 = query_params.get('refresh_token', [''])[0]
        is_encoded = query_params.get('encoded') == 'true'

        if access_token_b64 and refresh_token_b64:
            # Decodificar se vieram codificados em base64
            if is_encoded:
                import base64
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
            # Não fazer rerun aqui - deixar o fluxo continuar para verificar a sessão
            return

    # Se não temos tokens e não há query params, tentar carregar do localStorage via JavaScript
    st.markdown("""
        <script>
        (function() {
            const url = new URL(window.location);
            if (url.searchParams.has('auto_login')) {
                return;
            }
            
            const accessToken = localStorage.getItem('paics_access_token');
            const refreshToken = localStorage.getItem('paics_refresh_token');
            
            if (accessToken && refreshToken) {
                const accessTokenB64 = btoa(accessToken);
                const refreshTokenB64 = btoa(refreshToken);
                
                url.searchParams.set('auto_login', 'true');
                url.searchParams.set('access_token', accessTokenB64);
                url.searchParams.set('refresh_token', refreshTokenB64);
                url.searchParams.set('encoded', 'true');
                window.location.href = url.toString();
            }
        })();
        </script>
    """, unsafe_allow_html=True)


# PRIMEIRO: Aguardar um pouco para o JavaScript executar e adicionar restore_user_id aos query params
# O JavaScript executa no navegador, então precisamos dar tempo para ele executar
time.sleep(0.5)  # Delay inicial para JavaScript executar

# Verificar query params para restaurar sessão do banco
query_params = st.query_params
restore_user_id = query_params.get('restore_user_id', [''])[0]

# Se há user_id nos query params, tentar restaurar sessão do banco
if restore_user_id and not st.session_state.get('authenticated'):
    from auth.auth_utils import restore_session_from_db
    if restore_session_from_db(restore_user_id):
        # Sessão restaurada com sucesso, limpar query params
        st.query_params.clear()
        st.rerun()
    else:
        # Não conseguiu restaurar, limpar localStorage e redirecionar
        st.markdown("""
            <script>
            localStorage.removeItem('paics_user_id');
            localStorage.removeItem('paics_access_token');
            localStorage.removeItem('paics_refresh_token');
            </script>
        """, unsafe_allow_html=True)
        st.query_params.clear()
        st.switch_page("pages/login.py")

# Se não há user_id nos query params e não está autenticado, 
# tentar restaurar sessão diretamente do banco (sem depender do JavaScript)
if not restore_user_id and not st.session_state.get('authenticated') and not st.session_state.get('access_token'):
    from auth.auth_utils import try_restore_session_from_db
    if try_restore_session_from_db():
        # Sessão restaurada com sucesso
        st.rerun()
    else:
        # Não conseguiu restaurar, aguardar um pouco para o JavaScript tentar
        time.sleep(1.0)
        # Verificar novamente os query params (caso o JavaScript tenha adicionado)
        query_params = st.query_params
        restore_user_id = query_params.get('restore_user_id', [''])[0]
        
        if restore_user_id:
            from auth.auth_utils import restore_session_from_db
            if restore_session_from_db(restore_user_id):
                st.query_params.clear()
                st.rerun()
            else:
                st.switch_page("pages/login.py")
        else:
            # Não conseguiu restaurar de nenhuma forma
            st.switch_page("pages/login.py")

# Verificar tokens existentes ou sessão autenticada
if st.session_state.get('access_token') and st.session_state.get('refresh_token'):
    if not verify_and_refresh_session():
        # Tokens inválidos, limpar e redirecionar
        st.markdown("""
            <script>
            localStorage.removeItem('paics_user_id');
            localStorage.removeItem('paics_access_token');
            localStorage.removeItem('paics_refresh_token');
            </script>
        """, unsafe_allow_html=True)
        st.switch_page("pages/login.py")
elif not st.session_state.get('authenticated'):
    # Se não está autenticado e não há user_id para restaurar, redirecionar
    if not restore_user_id:
        st.switch_page("pages/login.py")

# Tentar verificar tokens se disponíveis
if st.session_state.get('access_token') and st.session_state.get('refresh_token'):
    # Limpar contador de tentativas se tiver tokens
    if 'auto_login_attempts' in st.session_state:
        del st.session_state['auto_login_attempts']
    
    if not verify_and_refresh_session():
        # Tokens inválidos, limpar e redirecionar para login
        st.markdown("""
            <script>
            localStorage.removeItem('paics_access_token');
            localStorage.removeItem('paics_refresh_token');
            </script>
        """, unsafe_allow_html=True)
        st.switch_page("pages/login.py")
elif not st.session_state.get('authenticated'):
    # Se não está autenticado e não há auto_login, verificar novamente
    query_params = st.query_params
    has_auto_login = query_params.get('auto_login') == 'true'
    
    if not has_auto_login:
        # Não há tokens e não há auto_login, redirecionar para login
        st.switch_page("pages/login.py")

if st.session_state.get('role') != 'admin':
    st.error("Acesso negado. Esta página é apenas para administradores.")
    st.stop()

# Inicializar componentes (necessário para verificação de primeiro acesso)
db = get_db()
requisicao_model = Requisicao(db.requisicoes)
laudo_model = Laudo(db.laudos)
user_model = User(db.users)
fatura_model = Fatura(db.faturas)
# VectorStore será importado lazy quando necessário (evita problemas com numpy/chromadb)

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
    st.title("👨‍⚕️ Admin Dashboard")
    user = get_current_user()
    if user:
        st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
        st.write(f"**Email:** {user.get('email')}")

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
        ["Requisições", "Laudos", "Usuários", "Financeiro", "Knowledge Base"],
        key="admin_nav"
    )

# Página principal baseada na seleção
if page == "Requisições":
    st.header("📋 Requisições de Laudos")

    # Filtros e Data
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        # Filtro de data - Padrão hoje
        filter_date = st.date_input("📅 Data", value=datetime.now().date())

        # Opção para mostrar todas as datas
        show_all_dates = st.checkbox("Mostrar todas as datas", value=False)

        if show_all_dates:
            start_dt = None
            end_dt = None
        else:
            start_dt = datetime.combine(filter_date, datetime.min.time())
            end_dt = datetime.combine(filter_date, datetime.max.time())

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
    requisicoes_periodo = requisicao_model.find_all(start_date=start_dt, end_date=end_dt)

    # Estatísticas rápidas baseadas no período filtrado
    pendentes_req = [r for r in requisicoes_periodo if r.get('status') == 'pendente']
    em_analise = [r for r in requisicoes_periodo if r.get('status') == 'em_analise']
    liberadas_req = [r for r in requisicoes_periodo if r.get('status') == 'liberado']

    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric("📋 Total no Período", len(requisicoes_periodo))
    with col_stat2:
        st.metric("⏳ Pendentes", len(pendentes_req), delta=len(pendentes_req)
                  if not show_all_dates else None, delta_color="off")
    with col_stat3:
        st.metric("🔍 Em Análise", len(em_analise))
    with col_stat4:
        st.metric("✅ Liberadas", len(liberadas_req))

    st.divider()

    # Buscar requisições com filtro de status e data
    status = None if status_filter == "Todos" else status_filter
    requisicoes = requisicao_model.find_all(status=status, start_date=start_dt, end_date=end_dt)

    # Aplicar filtros adicionais
    if tipo_filter != "Todos":
        requisicoes = [r for r in requisicoes if r.get('tipo_exame') == tipo_filter]

    if search_term:
        search_lower = search_term.lower().strip()

        def _searchable(r):
            parts = [
                r.get("paciente", ""), r.get("tutor", ""), r.get("clinica", ""),
                r.get("especie", ""), r.get("raca", ""), r.get(
                    "medico_veterinario_solicitante", ""),
                r.get("regiao_estudo", ""), r.get("suspeita_clinica", ""),
                r.get("historico_clinico", "") or r.get("observacoes", ""),
            ]
            return " ".join(p or "" for p in parts).lower()
        requisicoes = [r for r in requisicoes if search_lower in _searchable(r)]

    # Ordenação
    _status_order = {"pendente": 0, "em_analise": 1, "validado": 2, "liberado": 3, "rejeitado": 4}

    def _sort_key(r):
        dt = r.get("created_at") or datetime.min
        if "Status" in sort_by:
            return (_status_order.get(r.get("status"), 99), dt)
        if "Clínica" in sort_by:
            return (r.get("clinica", "").lower(), dt)
        if "Paciente" in sort_by:
            return (r.get("paciente", "").lower(), dt)
        return (dt,)

    reverse = "mais recente" in sort_by
    requisicoes = sorted(requisicoes, key=_sort_key, reverse=reverse)

    st.metric("Total de Requisições", len(requisicoes))

    def _fmt_dt(x):
        if x is None:
            return "—"
        if hasattr(x, "strftime"):
            return x.strftime("%d/%m/%Y %H:%M") if hasattr(x, "hour") else x.strftime("%d/%m/%Y")
        return str(x)[:16]

    # Lista de requisições
    for req in requisicoes:
        status_req = req.get("status", "N/A")
        status_label = {"pendente": "⏳ Pendente", "em_analise": "🔍 Em análise", "validado": "✅ Validado",
                        "liberado": "✅ Concluída", "rejeitado": "❌ Rejeitada"}.get(status_req, status_req)
        n_imgs = len(req.get("imagens") or [])

        with st.expander(f"📄 #{req['id'][:8]} · {req.get('paciente', 'Sem nome')} · {status_label} · {n_imgs} imagem(ns)"):
            laudo = laudo_model.find_by_requisicao(req["id"])
            user = user_model.find_by_id(req.get("user_id")) if req.get("user_id") else None

            if view_mode == "Rápida":
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Paciente:** {req.get('paciente', '—')}")
                    st.write(f"**Tutor:** {req.get('tutor', '—')}")
                    st.write(f"**Clínica:** {req.get('clinica', '—')}")
                with c2:
                    st.write(f"**Status:** {status_label}")
                    st.write(f"**Data:** {_fmt_dt(req.get('created_at') or req.get('data_exame'))}")
                    st.write(f"**Tipo:** {req.get('tipo_exame', '—')}")
                    st.write(f"**Imagens:** {n_imgs} arquivo(s)")
                with c3:
                    if user:
                        st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
                    if laudo:
                        st.info(f"📝 Laudo: {laudo.get('status', 'N/A')}")
                    else:
                        st.warning("⏳ Laudo não criado")
                # Galeria rápida (expander)
                if n_imgs:
                    with st.expander("🖼️ Ver imagens", expanded=False):
                        from ai.analyzer import load_images_for_analysis
                        imagens_paths = req.get("imagens") or []
                        for start in range(0, len(imagens_paths), 3):
                            cols = st.columns(3)
                            for k, path in enumerate(imagens_paths[start : start + 3]):
                                if k < len(cols):
                                    with cols[k]:
                                        nome = os.path.basename(path)
                                        try:
                                            loaded = load_images_for_analysis([path])
                                            prev = loaded[0] if loaded else None
                                        except Exception:
                                            prev = None
                                        if prev is not None:
                                            st.image(prev, use_container_width=True, caption=nome)
                                        else:
                                            st.caption(nome)
            else:
                st.subheader("📋 Dados completos da requisição")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**Paciente:**", req.get("paciente") or "—")
                    st.write("**Espécie:**", req.get("especie") or "—")
                    st.write("**Idade:**", req.get("idade") or "—")
                    st.write("**Raça:**", req.get("raca") or "—")
                    st.write("**Sexo:**", req.get("sexo") or "—")
                    st.write("**Tutor(a):**", req.get("tutor") or "—")
                    st.write("**Clínica solicitante:**", req.get("clinica") or "—")
                    st.write("**Médico(a) veterinário(a):**",
                             req.get("medico_veterinario_solicitante") or "—")
                with col_b:
                    st.write("**Região de estudo:**", req.get("regiao_estudo") or "—")
                    st.write("**Suspeita clínica:**", req.get("suspeita_clinica") or "—")
                    st.write("**Plantão:**", req.get("plantao") or "—")
                    st.write("**Data da requisição:**",
                             _fmt_dt(req.get("created_at") or req.get("data_exame")))
                    st.write("**Status:**", status_label)
                    st.write("**Tipo de exame:**", req.get("tipo_exame") or "—")
                    if user:
                        st.write("**Usuário:**", user.get("nome", user.get("username")),
                                 "·", user.get("email", ""))
                st.write("**Histórico clínico:**")
                hc = req.get("historico_clinico") or req.get("observacoes") or "—"
                st.text_area("", value=hc, height=80, disabled=True, key=f"hist_{req['id']}")

                # Galeria de imagens
                imagens_paths = req.get("imagens") or []
                if imagens_paths:
                    with st.expander(f"🖼️ Imagens anexadas ({len(imagens_paths)})", expanded=False):
                        from ai.analyzer import load_images_for_analysis
                        n_cols = 3
                        for start in range(0, len(imagens_paths), n_cols):
                            cols = st.columns(n_cols)
                            for k, path in enumerate(imagens_paths[start : start + n_cols]):
                                if k < len(cols):
                                    with cols[k]:
                                        nome = os.path.basename(path)
                                        preview = None
                                        try:
                                            loaded = load_images_for_analysis([path])
                                            preview = loaded[0] if loaded else None
                                        except Exception:
                                            pass
                                        if preview is not None:
                                            st.image(preview, use_container_width=True, caption=nome)
                                        else:
                                            st.caption(nome)
                                            st.caption("(prévia indisponível)")

            # Controle de edição inline
            editing_key = f"editing_{req['id']}"
            is_editing = st.session_state.get(editing_key, False)

            # Botão para iniciar/parar edição
            st.divider()
            col_btn_toggle, col_btn2, col_btn3, col_btn4 = st.columns(4)
            with col_btn_toggle:
                if is_editing:
                    if st.button("❌ Fechar Editor", key=f"close_edit_{req['id']}", use_container_width=True):
                        del st.session_state[editing_key]
                        st.rerun()
                else:
                    if st.button("📝 Gerar/Editar Laudo", key=f"edit_{req['id']}", use_container_width=True):
                        # Se não há laudo, gerar com IA primeiro
                        if not laudo:
                            try:
                                with st.spinner("🤖 Gerando laudo com IA..."):
                                    imagens_paths = req.get("imagens", [])
                                    if imagens_paths:
                                        from ai.analyzer import VetAIAnalyzer, load_images_for_analysis
                                        images = load_images_for_analysis(imagens_paths)
                                        if images:
                                            ai_analyzer = VetAIAnalyzer()
                                            # Preparar informações do paciente para a IA
                                            paciente_info = {
                                                "especie": req.get("especie", ""),
                                                "raca": req.get("raca", ""),
                                                "idade": req.get("idade", ""),
                                                "sexo": req.get("sexo", ""),
                                                "historico_clinico": req.get("historico_clinico", "") or req.get("observacoes", ""),
                                                "suspeita_clinica": req.get("suspeita_clinica", ""),
                                                "regiao_estudo": req.get("regiao_estudo", ""),
                                            }
                                            texto_gerado = ai_analyzer.generate_diagnosis(
                                                images, paciente_info)
                                            laudo_model.create(
                                                requisicao_id=req["id"],
                                                texto=texto_gerado,
                                                texto_original=texto_gerado,
                                                status="pendente",
                                            )
                                            st.success("✅ Laudo gerado com IA!")
                                            laudo = laudo_model.find_by_requisicao(req["id"])
                                        else:
                                            st.warning(
                                                "Nenhuma imagem válida. Criando laudo vazio para edição manual.")
                                            laudo_id = laudo_model.create(
                                                requisicao_id=req["id"],
                                                texto="",
                                                texto_original="",
                                                status="pendente",
                                            )
                                            laudo = laudo_model.find_by_id(laudo_id)
                                    else:
                                        st.warning(
                                            "Nenhuma imagem. Criando laudo vazio para edição manual.")
                                        laudo_id = laudo_model.create(
                                            requisicao_id=req["id"],
                                            texto="",
                                            texto_original="",
                                            status="pendente",
                                        )
                                        laudo = laudo_model.find_by_id(laudo_id)
                            except Exception as e:
                                st.warning(f"⚠️ Erro ao gerar laudo: {str(e)}")
                                # Criar laudo vazio mesmo assim
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
                if req.get("status") == "pendente":
                    if st.button("✅ Iniciar Análise", key=f"start_{req['id']}", use_container_width=True):
                        requisicao_model.update_status(req["id"], "em_analise")
                        st.success("Análise iniciada")
                        st.rerun()
            with col_btn3:
                if laudo and laudo.get("status") in ("pendente", "validado") and not is_editing:
                    if st.button("📤 Aprovar/Liberar", key=f"approve_{req['id']}", use_container_width=True):
                        laudo_model.release(laudo["id"])
                        requisicao_model.update_status(req["id"], "liberado")
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
                            import base64
                            from io import BytesIO

                            # Preparar dados das imagens e converter para base64
                            images_data = []
                            for i, path in enumerate(imagens_paths):
                                nome = os.path.basename(path)
                                preview = None

                                try:
                                    loaded = load_images_for_analysis([path])
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
                                    'path': path,
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
                            buf = io.BytesIO()
                            added = 0
                            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                                for i, path in enumerate(imagens_paths):
                                    nome = os.path.basename(path)
                                    arcname = f"{i + 1}_{nome}"
                                    try:
                                        with open(path, "rb") as f:
                                            zf.writestr(arcname, f.read())
                                        added += 1
                                    except Exception:
                                        pass
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
                        # Aumentar altura do editor para ocupar mais espaço disponível
                        texto_editado = st.text_area(
                            "Conteúdo do laudo",
                            value=laudo.get("texto", ""),
                            height=600,
                            key=editor_key,
                        )

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if st.button("💾 Salvar", use_container_width=True, key=f"save_inline_{laudo['id']}"):
                                laudo_model.update(laudo["id"], {"texto": texto_editado})
                                st.success("Laudo salvo!")
                                st.rerun()
                        with col2:
                            if st.button("✅ Validar", use_container_width=True, key=f"val_inline_{laudo['id']}"):
                                user = get_current_user()
                                laudo_model.validate(laudo["id"], user["id"])
                                requisicao_model.update_status(req["id"], "validado")
                                try:
                                    from vector_db.vector_store import VectorStore
                                    vector_store = VectorStore()
                                    vector_store.add_laudo(
                                        laudo["id"],
                                        texto_editado,
                                        metadata={
                                            "paciente": req.get("paciente"),
                                            "tipo_exame": req.get("tipo_exame"),
                                            "status": "validado",
                                        },
                                    )
                                    st.success(
                                        "Laudo validado e adicionado ao banco de aprendizado!")
                                except Exception as vec_err:
                                    st.success("Laudo validado!")
                                    st.warning(
                                        f"Não foi possível adicionar ao banco vetorial (chromadb/rpds): {vec_err!s}. "
                                        "Execute `just fix-rpds` ou use Python 3.11/3.12."
                                    )
                                st.rerun()
                        with col3:
                            if st.button("📤 Liberar", use_container_width=True, key=f"lib_inline_{laudo['id']}"):
                                laudo_model.release(laudo["id"])
                                requisicao_model.update_status(req["id"], "liberado")
                                st.success(
                                    "✅ Laudo liberado para o usuário! Ele poderá visualizar e fazer download agora.")
                                st.balloons()
                                del st.session_state[editing_key]
                                st.rerun()
                        with col4:
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

elif page == "Laudos":
    st.header("📝 Gerenciamento de Laudos")

    # Estatísticas rápidas
    todos_laudos = laudo_model.find_all()
    pendentes = [l for l in todos_laudos if l.get('status') == 'pendente']
    validados = [l for l in todos_laudos if l.get('status') == 'validado']
    liberados = [l for l in todos_laudos if l.get('status') == 'liberado']

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total", len(todos_laudos))
    with col2:
        st.metric("⏳ Pendentes", len(pendentes), delta=len(pendentes), delta_color="off")
    with col3:
        st.metric("✅ Validados", len(validados))
    with col4:
        st.metric("📤 Liberados", len(liberados))

    # Nota: A edição de laudos agora é feita inline na aba "Requisições"
    # Esta aba serve como lista de consulta/visualização
    st.info("💡 **Dica:** A edição de laudos é feita diretamente na aba **Requisições**. Use esta aba para consulta e visualização.")
    st.divider()

    # Lista de laudos (apenas pendentes por padrão)
    st.subheader("📋 Lista de Laudos")

    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Apenas pendentes", "Todos", "pendente", "validado", "liberado", "rejeitado"],
            index=0,
            help="Por padrão, apenas laudos pendentes de revisão."
        )
    with col2:
        search_term = st.text_input("🔍 Buscar (paciente/tutor/clínica)")
    with col3:
        sort_laudos = st.selectbox(
            "Ordenar", ["Mais recentes", "Mais antigos", "Paciente", "Clínica"], key="laudo_sort")

    if status_filter == "Apenas pendentes":
        status = "pendente"
    elif status_filter == "Todos":
        status = None
    else:
        status = status_filter
    laudos = laudo_model.find_all(status=status)

    # Aplicar busca (paciente, tutor, clínica)
    if search_term:
        search_lower = search_term.lower().strip()
        laudos_filtrados = []
        for laudo in laudos:
            req = requisicao_model.find_by_id(laudo.get("requisicao_id"))
            if req:
                if (search_lower in (req.get("paciente") or "").lower()
                        or search_lower in (req.get("tutor") or "").lower()
                        or search_lower in (req.get("clinica") or "").lower()):
                    laudos_filtrados.append(laudo)
        laudos = laudos_filtrados

    # Ordenar
    def _laudo_sort_key(l):
        req = requisicao_model.find_by_id(l.get("requisicao_id"))
        dt = l.get("created_at") or datetime.min
        if "Mais antigos" in sort_laudos:
            return (dt,)
        if "Paciente" in sort_laudos:
            return ((req or {}).get("paciente", "").lower(), dt)
        if "Clínica" in sort_laudos:
            return ((req or {}).get("clinica", "").lower(), dt)
        return (dt,)

    reverse = "Mais recentes" in sort_laudos
    laudos_ordenados = sorted(laudos, key=_laudo_sort_key, reverse=reverse)

    if status_filter == "Apenas pendentes":
        st.info("📋 **Mostrando apenas laudos pendentes** de revisão. Altere o filtro para ver validados ou liberados.")

    if not laudos_ordenados:
        st.info("Nenhum laudo encontrado com os filtros selecionados.")
    else:
        for laudo in laudos_ordenados:
            req = requisicao_model.find_by_id(laudo.get('requisicao_id'))

            # Badge de status
            status_badge = {
                "pendente": "⏳ Pendente - Aguardando Revisão",
                "validado": "✅ Validado",
                "liberado": "📤 Liberado",
                "rejeitado": "❌ Rejeitado"
            }.get(laudo.get('status'), laudo.get('status'))

            paciente_nome = req.get('paciente', 'N/A') if req else 'N/A'

            with st.expander(f"📄 {paciente_nome} - {status_badge} - #{laudo['id'][:8]}"):
                col1, col2 = st.columns(2)

                with col1:
                    if req:
                        st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                        st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                        st.write(f"**Tipo de Exame:** {req.get('tipo_exame', 'N/A')}")

                    # Buscar usuário
                    if req:
                        user = user_model.find_by_id(req.get('user_id'))
                        if user:
                            st.write(f"**Cliente:** {user.get('nome', user.get('username'))}")

                with col2:
                    st.write(f"**Status:** {status_badge}")
                    st.write(f"**Criado em:** {laudo.get('created_at', 'N/A')}")
                    if laudo.get('validado_at'):
                        st.write(f"**Validado em:** {laudo.get('validado_at')}")
                    if laudo.get('liberado_at'):
                        st.write(f"**Liberado em:** {laudo.get('liberado_at')}")

                # Preview do laudo
                st.divider()
                st.subheader("📝 Conteúdo do Laudo")
                texto_preview = laudo.get('texto', '')[
                    :500] + "..." if len(laudo.get('texto', '')) > 500 else laudo.get('texto', '')
                st.text_area("Preview", texto_preview, height=150,
                             disabled=True, key=f"preview_{laudo['id']}")

                # Ações - redirecionar para Requisições para editar
                col_btn1, col_btn2, col_btn3 = st.columns(3)

                with col_btn1:
                    if st.button("✏️ Editar na aba Requisições", key=f"edit_laudo_{laudo['id']}", use_container_width=True):
                        st.info(
                            "💡 **Vá para a aba 'Requisições' e clique em 'Gerar/Editar Laudo' na requisição correspondente para editar inline.**")
                        st.rerun()

                with col_btn2:
                    if laudo.get('status') == 'pendente':
                        if st.button("✅ Validar", key=f"validate_{laudo['id']}", use_container_width=True):
                            user = get_current_user()
                            laudo_model.validate(laudo['id'], user['id'])
                            if req:
                                requisicao_model.update_status(req.get('id'), 'validado')
                            st.success("Laudo validado!")
                            st.rerun()

                with col_btn3:
                    if laudo.get('status') in ['pendente', 'validado']:
                        if st.button("📤 Liberar", key=f"release_{laudo['id']}", use_container_width=True):
                            laudo_model.release(laudo['id'])
                            if req:
                                requisicao_model.update_status(req.get('id'), 'liberado')
                            st.success("✅ Laudo liberado para o usuário!")
                            st.balloons()
                            st.rerun()

elif page == "Usuários":
    st.header("👥 Gerenciamento de Usuários")

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
                st.write(f"**Username:** {user.get('username')}")
                st.write(f"**Email:** {user.get('email')}")
                st.write(f"**Nome Completo:** {user.get('nome', 'N/A')}")
                st.write(
                    f"**Tipo:** {'👨‍⚕️ Administrador' if user.get('role') == 'admin' else '👤 Cliente'}")
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
        else:
            st.error("Usuário não encontrado")
            del st.session_state['viewing_user']
            st.rerun()

    else:
        tab1, tab2 = st.tabs(["Cadastrar Novo Usuário", "Listar Usuários"])

        with tab1:
            st.subheader("➕ Cadastrar Novo Usuário/Cliente")
            st.info("ℹ️ O sistema gerará uma senha temporária automaticamente. O usuário será obrigado a alterar a senha no primeiro acesso.")

            # Mostrar feedback de cadastro bem-sucedido
            if st.session_state.get('user_created') and st.session_state.get('new_user_credentials'):
                creds = st.session_state['new_user_credentials']
                st.success(f"✅ Usuário cadastrado com sucesso! ID: {creds['user_id'][:8]}")
                st.balloons()

                # Mostrar credenciais temporárias em destaque
                st.markdown("---")
                st.markdown("### 📋 Credenciais Temporárias")
                st.warning(
                    "⚠️ **IMPORTANTE:** Compartilhe essas credenciais com o usuário. Ele será obrigado a alterar a senha no primeiro acesso.")

                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown(f"**Username:** `{creds['username']}`")
                    st.markdown(f"**Email:** `{creds['email']}`")
                with col_info2:
                    st.markdown(f"**Tipo:** `{creds['role']}`")
                    st.markdown(f"**Senha Temporária:** `{creds['senha_temporaria']}`")

                # Botão para copiar credenciais
                st.code(
                    f"Email: {creds['email']}\nSenha Temporária: {creds['senha_temporaria']}", language="")

                # Botão para limpar feedback
                if st.button("✖️ Fechar", key="close_user_feedback"):
                    del st.session_state['user_created']
                    del st.session_state['new_user_credentials']
                    st.rerun()

                st.markdown("---")

            with st.form("cadastrar_usuario"):
                col1, col2 = st.columns(2)

                with col1:
                    nome = st.text_input("Nome Completo *")
                    username = st.text_input("Username *")
                    email = st.text_input("Email *")

                with col2:
                    role = st.selectbox("Tipo de Usuário", [
                                        "user", "admin"], help="'user' para clientes, 'admin' para administradores")
                    ativo = st.checkbox("Usuário Ativo", value=True)

                submit = st.form_submit_button(
                    "✅ Cadastrar Usuário", type="primary", use_container_width=True)

                if submit:
                    # Validações
                    if not all([nome, username, email]):
                        st.error("❌ Por favor, preencha todos os campos obrigatórios!")
                    else:
                        # Verificar se email ou username já existem
                        if user_model.find_by_email(email):
                            st.error(f"❌ Email {email} já está cadastrado!")
                        elif user_model.find_by_username(username):
                            st.error(f"❌ Username {username} já está em uso!")
                        else:
                            try:
                                import secrets
                                import string
                                from auth.auth_utils import hash_password

                                # Gerar senha temporária (8 caracteres alfanuméricos)
                                alphabet = string.ascii_letters + string.digits
                                senha_temporaria = ''.join(secrets.choice(alphabet)
                                                           for i in range(8))

                                # Criar hash da senha temporária
                                password_hash = hash_password(senha_temporaria)

                                # Criar usuário com primeiro_acesso=True
                                user_id = user_model.create(
                                    username=username,
                                    email=email,
                                    password_hash=password_hash,
                                    role=role,
                                    nome=nome,
                                    ativo=ativo,
                                    primeiro_acesso=True,
                                    senha_temporaria=senha_temporaria
                                )

                                # Salvar informações na sessão para mostrar após rerun
                                st.session_state['user_created'] = True
                                st.session_state['new_user_credentials'] = {
                                    'username': username,
                                    'email': email,
                                    'role': role,
                                    'senha_temporaria': senha_temporaria,
                                    'user_id': user_id
                                }

                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao cadastrar usuário: {str(e)}")
                                import traceback
                                st.exception(e)

        with tab2:
            st.subheader("📋 Lista de Usuários")

            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                role_filter = st.selectbox("Filtrar por Tipo", ["Todos", "user", "admin"])
            with col2:
                status_filter = st.selectbox("Filtrar por Status", ["Todos", "Ativo", "Inativo"])

            # Buscar usuários
            role = None if role_filter == "Todos" else role_filter
            users = user_model.get_all(role=role)

            # Filtrar por status
            if status_filter == "Ativo":
                users = [u for u in users if u.get('ativo', True)]
            elif status_filter == "Inativo":
                users = [u for u in users if not u.get('ativo', True)]

            st.metric("Total de Usuários", len(users))

            for user in users:
                status_badge = "✅ Ativo" if user.get('ativo', True) else "🚫 Inativo"
                role_badge = "👨‍⚕️ Admin" if user.get('role') == 'admin' else "👤 Cliente"

                with st.expander(f"{role_badge} {user.get('nome', user.get('username'))} - {status_badge}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Username:** {user.get('username')}")
                        st.write(f"**Email:** {user.get('email')}")
                        st.write(f"**Nome:** {user.get('nome', 'N/A')}")
                        st.write(f"**Tipo:** {role_badge}")
                        st.write(f"**Status:** {status_badge}")
                        st.write(f"**Cadastrado em:** {user.get('created_at', 'N/A')}")

                    with col2:
                        # Estatísticas do usuário
                        reqs = requisicao_model.find_by_user(user['id'])
                        laudos = laudo_model.find_by_user(user['id'])
                        laudos_liberados = [l for l in laudos if l.get('status') == 'liberado']

                        st.metric("📋 Requisições", len(reqs))
                        st.metric("📝 Laudos", len(laudos))
                        st.metric("✅ Laudos Liberados", len(laudos_liberados))

                        # Ações
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
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
                            # Não permitir excluir o próprio usuário
                            current_user = get_current_user()
                            if current_user and current_user.get('id') == user['id']:
                                st.button("🗑️ Excluir", key=f"delete_{user['id']}", disabled=True, use_container_width=True,
                                          help="Você não pode excluir seu próprio usuário")
                            else:
                                # Verificar se é o admin dummy
                                is_dummy = user.get('username') == 'admin' and user.get(
                                    'email') == 'admin@paics.local'

                                # Verificar se tem dados associados
                                has_data = len(reqs) > 0 or len(laudos) > 0

                                if has_data and not is_dummy:
                                    st.button("🗑️ Excluir", key=f"delete_{user['id']}", disabled=True, use_container_width=True,
                                              help=f"Usuário possui {len(reqs)} requisição(ões) e {len(laudos)} laudo(s). Desative em vez de excluir.")
                                else:
                                    delete_key = f"delete_{user['id']}"
                                    if st.button("🗑️ Excluir", key=delete_key, use_container_width=True):
                                        # Verificar confirmação
                                        if not st.session_state.get(f"confirm_{delete_key}", False):
                                            st.session_state[f"confirm_{delete_key}"] = True
                                            st.warning(
                                                f"⚠️ Clique novamente em 'Excluir' para confirmar a exclusão de '{user.get('username')}'")
                                            if is_dummy:
                                                st.info(
                                                    "💡 Certifique-se de ter criado seu próprio usuário administrador antes de excluir o dummy.")
                                            st.rerun()
                                        else:
                                            # Confirmar exclusão
                                            if user_model.delete(user['id']):
                                                del st.session_state[f"confirm_{delete_key}"]
                                                if is_dummy:
                                                    st.success(
                                                        "✅ Usuário dummy excluído com sucesso!")
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
            data_inicio = st.date_input("Data Início", value=datetime.now().replace(day=1).date())
        with col2:
            data_fim = st.date_input("Data Fim", value=datetime.now().date())
        with col3:
            valor_exame = st.number_input("Valor por Exame (R$)",
                                          min_value=0.0, value=50.0, step=1.0)

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("📊 Gerar Fechamento (Todos Usuários)", use_container_width=True):
                from utils.financeiro import gerar_fechamento_todos_usuarios, criar_fatura

                try:
                    fechamentos = gerar_fechamento_todos_usuarios(
                        datetime.combine(data_inicio, datetime.min.time()),
                        datetime.combine(data_fim, datetime.max.time()),
                        valor_exame
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
                from utils.financeiro import gerar_fechamento, criar_fatura

                # Extrair user_id do selecionado
                user_idx = usuarios.index(
                    [u for u in usuarios if f"{u.get('nome', u.get('username'))} ({u.get('email')})" == usuario_selecionado][0])
                user_selected = usuarios[user_idx]

                try:
                    fechamento = gerar_fechamento(
                        user_selected['id'],
                        datetime.combine(data_inicio, datetime.min.time()),
                        datetime.combine(data_fim, datetime.max.time()),
                        valor_exame
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
        col1, col2 = st.columns(2)
        with col1:
            periodo_filter = st.text_input("🔍 Filtrar por Período (opcional)")
        with col2:
            status_filter = st.selectbox(
                "Filtrar por Status",
                ["Todos", "pendente", "paga", "cancelada"]
            )

        # Buscar faturas
        status = None if status_filter == "Todos" else status_filter
        faturas = fatura_model.find_all(status=status)

        if periodo_filter:
            faturas = [f for f in faturas if periodo_filter in f.get('periodo', '')]

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
                        st.write(f"**Email:** {user.get('email')}")
                    st.write(f"**Período:** {fatura.get('periodo')}")
                    st.write(f"**Valor Total:** R$ {fatura.get('valor_total', 0):.2f}")
                    st.write(f"**Status:** {fatura.get('status')}")
                    st.write(f"**Criada em:** {fatura.get('created_at')}")

                with col2:
                    st.write(f"**Quantidade de Exames:** {len(fatura.get('exames', []))}")

                    # Lista de exames
                    if fatura.get('exames'):
                        st.write("**Exames:**")
                        for exame in fatura.get('exames', [])[:10]:  # Mostrar até 10
                            st.write(
                                f"- {exame.get('paciente', 'N/A')} ({exame.get('tipo_exame', 'N/A')}) - R$ {exame.get('valor', 0):.2f}")
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

elif page == "Knowledge Base":
    st.header("📚 Knowledge Base")

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
                        # Salvar arquivo temporariamente
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            tmp_path = tmp_file.name

                        tags = [t.strip() for t in tags_input.split(
                            ',') if t.strip()] if tags_input else []
                        kb_id = kb_manager.add_pdf(tmp_path, titulo, tags)
                        st.success(f"✅ PDF adicionado com sucesso! ID: {kb_id[:8]}")

                        # Limpar arquivo temporário
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
