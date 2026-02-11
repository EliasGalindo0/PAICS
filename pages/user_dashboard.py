"""
Dashboard do Usuário
"""
import time
from utils.theme import apply_custom_theme
from utils.observability import log
import streamlit as st
from datetime import datetime
from auth.auth_utils import get_current_user, clear_session, logout_user, verify_and_refresh_session
from utils.timezone import now, utc_to_local
from database.connection import get_db
from database.models import Requisicao, Laudo, User, Clinica, Veterinario
import os
import tempfile
import io
from fpdf import FPDF
from fpdf.enums import XPos, YPos
# PIL.Image será importado lazy quando necessário (evita problemas com Python 3.13)

# IMPORTANTE: st.set_page_config deve vir PRIMEIRO
st.set_page_config(
    page_title="Dashboard Usuário - PAICS",
    page_icon="👤",
    layout="wide",
    menu_items=None
)

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

# Aplicar tema customizado
apply_custom_theme()

# Ocultar menu de navegação de páginas e reduzir margem superior
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    /* Reduzir margem superior */
    .main .block-container {
        padding-top: 0.5rem !important;
    }
    /* Remover sombras e bordas no modo escuro */
    [data-theme="dark"] .main .block-container,
    [data-theme="dark"] .element-container {
        box-shadow: none !important;
        background: transparent !important;
    }
    [data-theme="dark"] section[data-testid="stSidebar"] {
        border-right: none !important;
    }
    [data-theme="dark"] section[data-testid="stSidebar"] > div:first-child {
        border-top: none !important;
        border-bottom: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Script já foi movido para o início do arquivo para garantir execução antes do Python

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
time.sleep(0.3)  # Pequeno delay para JavaScript executar

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

if st.session_state.get('role') == 'admin':
    st.switch_page("pages/admin_dashboard.py")

# Inicializar componentes (necessário para verificação de primeiro acesso)
db = get_db()
requisicao_model = Requisicao(db.requisicoes)
laudo_model = Laudo(db.laudos)
user_model = User(db.users)
clinica_model = Clinica(db.clinicas)
veterinario_model = Veterinario(db.veterinarios)

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
    # Botão de alternar tema
    from utils.theme import theme_toggle_button
    theme_toggle_button()
    st.divider()

    st.title("👤 Meu Dashboard")
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

    # Navegação (Meus Laudos como primeira aba ao abrir)
    page = st.radio(
        "Navegação",
        ["Exames", "Nova Requisição", "Minhas Faturas"],
        key="user_nav"
    )

# Página principal
if page == "Exames":
    st.header("📋 Meus Exames")

    # Notificação de laudos recém liberados
    import datetime as _dt
    _now = now()
    _last = st.session_state.get("last_meus_exames_visit")
    st.session_state["last_meus_exames_visit"] = _now
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

    # Filtros (padrão: apenas liberados + data atual — carrega menos e é mais leve ao abrir)
    col1, col2, col3 = st.columns(3)
    with col1:
        status = st.selectbox(
            "Filtrar por status",
            ["Todos", "Liberados", "Pendente", "Validado"],
            index=0,
            key="exame_status_filter"
        )
    with col2:
        filter_date = st.date_input("📅 Data", value=now().date(), key="exame_date_filter")
        show_all_dates = st.checkbox("Mostrar todas as datas",
                                     value=False, key="exame_show_all_dates")
    with col3:
        st.write("")

    _uid = st.session_state.get("user_id")
    status_map = {"Todos": None, "Pendente": "pendente",
                  "Validado": "validado", "Liberados": "liberado"}
    status_val = status_map.get(status)

    # Carregamento leve: quando "Apenas liberados", busca só laudos liberados (e suas reqs)
    if status == "Liberados":
        exames_liberados = laudo_model.find_by_user(_uid, status="liberado") if _uid else []
        items = []
        for exame in exames_liberados:
            req = requisicao_model.find_by_id(exame.get("requisicao_id"))
            if req and req.get("status") != "rascunho":
                items.append((req, exame))
        filtered = items
    else:
        all_reqs = [r for r in (requisicao_model.find_by_user(
            _uid) if _uid else []) if r.get("status") != "rascunho"]
        items = []
        for req in all_reqs:
            exame = laudo_model.find_by_requisicao(req["id"])
            items.append((req, exame))
        if status_val == "pendente":
            filtered = [(r, l) for r, l in items if l is None or l.get("status") == "pendente"]
        elif status_val == "validado":
            filtered = [(r, l) for r, l in items if l and l.get("status") == "validado"]
        else:
            filtered = items

    # Filtro por data: inicialmente apenas requisições do dia selecionado
    if not show_all_dates:
        def _req_date(req):
            d = req.get("created_at") or req.get("data_exame")
            if d is None:
                return None
            # Converter para datetime se for string
            if isinstance(d, str):
                try:
                    d = datetime.fromisoformat(d.replace("Z", "+00:00")[:26])
                except Exception:
                    try:
                        # Tentar parsear formato alternativo
                        from dateutil import parser
                        d = parser.parse(d)
                    except Exception:
                        return None
            # Se não for datetime, retornar None
            if not isinstance(d, datetime):
                return None
            # Se for naive, assumir que veio em UTC (Mongo) e converter para local
            from datetime import timezone as _tzmod
            if d.tzinfo is None:
                d = d.replace(tzinfo=_tzmod.utc)
            # Converter para horário local (GMT-3)
            d = utc_to_local(d)
            return d.date() if hasattr(d, "date") else d

        filtered = [(r, l) for r, l in filtered if _req_date(r) == filter_date]

    if status == "Liberados":
        st.info("📋 **Mostrando apenas laudos liberados.** Altere o filtro para ver pendentes, validados ou aguardando laudo.")
    if not show_all_dates:
        st.caption(
            f"📅 Exibindo requisições de **{filter_date.strftime('%d/%m/%Y')}**. Marque «Mostrar todas as datas» para ver o histórico.")

    st.metric("Total", len(filtered))

    # Helper local para formatar datas em GMT-3 na seção "Meus Laudos"
    from datetime import datetime as _UDDateTime, timezone as _UDTimezone
    from utils.timezone import utc_to_local as _ud_utc_to_local

    def _fmt_dt_meus_laudos(x):
        if x is None:
            return "—"
        if isinstance(x, _UDDateTime):
            # Valores gravados no Mongo sem tz são UTC por padrão
            if x.tzinfo is None:
                x = x.replace(tzinfo=_UDTimezone.utc)
            x_local = _ud_utc_to_local(x)
            return x_local.strftime("%d/%m/%Y %H:%M")
        return str(x)

    if not filtered:
        st.info("Você ainda não possui requisições ou laudos. Envie uma nova requisição para começar!")
    else:
        for req, laudo in filtered:
            if laudo is None:
                status_badge = "⏳ Aguardando laudo"
                with st.expander(f"**{req.get('paciente', 'N/A')}** – {req.get('tutor', 'N/A')} – {status_badge}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                        st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                        st.write(f"**Tipo de Exame:** {req.get('tipo_exame', 'N/A')}")
                    with col2:
                        st.write(f"**Status:** {status_badge}")
                        st.write(f"**Requisição em:** {_fmt_dt_meus_laudos(req.get('created_at'))}")
                    st.divider()
                    st.subheader("📝 Aguardando laudo")
                    st.info("📤 Requisição enviada. O laudo será criado e liberado pelo veterinário administrador. Você será notificado quando estiver disponível para download.")
                    # Observações adicionais (usuário não pode editar a requisição, apenas enviar notas)
                    _obs_list = req.get("observacoes_usuario") or []
                    if _obs_list:
                        with st.expander("📌 Observações que você enviou", expanded=False):
                            for _i, _ob in enumerate(reversed(_obs_list)):
                                _t = _ob.get("texto", "")
                                _d = _ob.get("created_at", "")
                                if _d and hasattr(_d, "strftime"):
                                    _d = _d.strftime("%d/%m/%Y %H:%M")
                                st.text_area("", value=_t, height=60, disabled=True,
                                             key=f"obs_read_{req['id']}_{_i}")
                                st.caption(f"Enviado em {_d}")
                    with st.expander("➕ Adicionar observação", expanded=False):
                        st.caption(
                            "Enviou algo errado ou lembrou de algum detalhe? Adicione aqui. O administrador verá e poderá considerar no laudo. Você não pode alterar os dados já enviados.")
                        with st.form(f"form_obs_{req['id']}"):
                            _novo_obs = st.text_area(
                                "Sua observação", height=100, key=f"obs_new_{req['id']}", placeholder="Ex.: A idade correta é 8 anos. O tutor informou que o animal manca da pata direita.")
                            if st.form_submit_button("Enviar observação"):
                                if _novo_obs and _novo_obs.strip():
                                    if requisicao_model.add_observacao_usuario(req["id"], _novo_obs.strip(), _user_id or ""):
                                        st.success(
                                            "Observação enviada. O administrador poderá considerá-la no laudo.")
                                        st.rerun()
                                else:
                                    st.warning("Digite uma observação.")
                continue

            status_badge = {"pendente": "⏳ Pendente", "validado": "✅ Validado",
                            "liberado": "✅ Concluído"}.get(laudo.get("status"), laudo.get("status"))
            with st.expander(f"**{req.get('paciente', 'N/A')}** – {req.get('tutor', 'N/A')} – {status_badge}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                    st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                    st.write(f"**Tipo de Exame:** {req.get('tipo_exame', 'N/A')}")
                with col2:
                    st.write(f"**Status:** {status_badge}")
                    st.write(f"**Criado em:** {_fmt_dt_meus_laudos(laudo.get('created_at'))}")
                    if laudo.get('validado_at'):
                        st.write(
                            f"**Validado em:** {_fmt_dt_meus_laudos(laudo.get('validado_at'))}")
                    if laudo.get('liberado_at'):
                        st.write(
                            f"**Liberado em:** {_fmt_dt_meus_laudos(laudo.get('liberado_at'))}")

                if laudo.get("status") == "pendente":
                    st.divider()
                    st.subheader("📝 Laudo Pendente")
                    st.info("⏳ Este laudo está aguardando revisão e validação do administrador.")
                elif laudo.get("status") == "validado":
                    st.divider()
                    st.subheader("📝 Laudo Validado")
                    st.warning("✅ Este laudo foi validado e está aguardando liberação.")
                if laudo.get("status") in ("pendente", "validado"):
                    # Observações adicionais (sem editar a requisição)
                    _obs_list = req.get("observacoes_usuario") or []
                    if _obs_list:
                        with st.expander("📌 Observações que você enviou", expanded=False):
                            for _j, _ob in enumerate(reversed(_obs_list)):
                                _t = _ob.get("texto", "")
                                _d = _ob.get("created_at", "")
                                if _d and hasattr(_d, "strftime"):
                                    _d = _d.strftime("%d/%m/%Y %H:%M")
                                st.text_area("", value=_t, height=60, disabled=True,
                                             key=f"obs_li_{req['id']}_{_j}")
                                st.caption(f"Enviado em {_d}")
                    with st.expander("➕ Adicionar observação", expanded=False):
                        st.caption(
                            "Enviou algo errado ou lembrou de algum detalhe? Adicione aqui. O administrador verá e poderá considerar no laudo.")
                        with st.form(f"form_obs_li_{req['id']}"):
                            _novo_obs_li = st.text_area(
                                "Sua observação", height=100, key=f"obs_new_li_{req['id']}", placeholder="Ex.: Idade correta 8 anos; animal manca da pata direita.")
                            if st.form_submit_button("Enviar observação"):
                                if _novo_obs_li and _novo_obs_li.strip():
                                    if requisicao_model.add_observacao_usuario(req["id"], _novo_obs_li.strip(), _user_id or ""):
                                        st.success("Observação enviada.")
                                        st.rerun()
                                else:
                                    st.warning("Digite uma observação.")
                if laudo.get("status") == "liberado":
                    st.divider()
                    st.subheader("📝 Laudo Liberado")
                    st.success("✅ Este laudo foi liberado e está disponível para download!")
                    st.text_area("Conteúdo do Laudo", value=laudo.get("texto", ""),
                                 height=300, disabled=True, key=f"liberado_{laudo['id']}")
                    try:
                        from ai.analyzer import load_images_for_analysis
                        imagens_paths = req.get("imagens", [])
                        images = load_images_for_analysis(imagens_paths)
                        # Resolver clínica e veterinário (requisição → usuário da requisição)
                        _clinica_pdf = req.get("clinica") or ""
                        if req.get("clinica_id"):
                            c_obj = clinica_model.find_by_id(req["clinica_id"])
                            if c_obj:
                                _clinica_pdf = c_obj.get("nome", "") or _clinica_pdf
                        if not (_clinica_pdf or "").strip() and req.get("user_id"):
                            _user_req = user_model.find_by_id(req["user_id"])
                            if _user_req and _user_req.get("clinica_id"):
                                c_obj = clinica_model.find_by_id(_user_req["clinica_id"])
                                _clinica_pdf = (c_obj or {}).get("nome", "") or _clinica_pdf
                        _vet_pdf = req.get("medico_veterinario_solicitante") or ""
                        if req.get("veterinario_id"):
                            v_obj = veterinario_model.find_by_id(req["veterinario_id"])
                            if v_obj:
                                _vet_pdf = v_obj.get("nome", "") or _vet_pdf
                        if not (_vet_pdf or "").strip() and req.get("user_id"):
                            _user_req = user_model.find_by_id(req["user_id"])
                            if _user_req and _user_req.get("clinica_id"):
                                vets = veterinario_model.find_by_clinica(
                                    _user_req["clinica_id"], apenas_ativos=True)
                                _vet_pdf = (vets[0].get("nome") if vets else None) or _vet_pdf
                        pdf = FPDF("P", "mm", "A4")
                        pdf.set_auto_page_break(auto=True, margin=15)

                        def _clean(t):
                            t = str(t) if t is not None else ""
                            for a, b in [("'", "'"), ("'", "'"), (""", '"'), (""", '"'), ("—", "-"), ("–", "-"), ("…", "..."), ("°", " graus")]:
                                t = t.replace(a, b)
                            t = t.replace("**", "")
                            try:
                                t.encode("latin-1")
                            except UnicodeEncodeError:
                                import unicodedata
                                t = unicodedata.normalize("NFKD", t).encode(
                                    "latin-1", "ignore").decode("latin-1")
                            return t
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 14)
                        pdf.ln(5)
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(
                            0, 6, f"Paciente: {_clean(req.get('paciente', 'N/A'))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.cell(0, 6, f"Tutor: {_clean(req.get('tutor', 'N/A'))}",
                                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.cell(
                            0, 6, f"Clinica Solicitante: {_clean(_clinica_pdf or 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.cell(
                            0, 6, f"Medico(a) Veterinario(a): {_clean(_vet_pdf or 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.cell(0, 6, f"Data: {now().strftime('%d/%m/%Y')}",
                                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(4)
                        pdf.set_font("Arial", "B", 12)
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
                                pdf.cell(0, 6, f"Imagem {i + 1}",
                                         new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                                pdf.ln(4)
                        pdf.set_y(-35)
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(0, 10, "_" * 60, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                        pdf.ln(2)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(0, 5, "Dra. Laís Costa Muchiutti",
                                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
                        pdf.ln(2)
                        pdf.set_font("Arial", "", 9)
                        pdf.cell(0, 5, "Medica Veterinaria-CRMV SP32247",
                                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        out = pdf.output(dest="S")
                        out = bytes(out) if isinstance(out, bytearray) else out
                        st.download_button(
                            "📥 Baixar como PDF", data=out, file_name=f"laudo_{req.get('paciente', 'exame').replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True, key=f"dl_pdf_{laudo['id']}")
                    except Exception as e:
                        st.error(f"Erro ao gerar PDF: {e}")
                        import traceback
                        traceback.print_exc()
                        st.download_button("📥 Baixar como PDF", data="", file_name="laudo.pdf", mime="application/pdf",
                                           disabled=True, use_container_width=True, key=f"dl_pdf_err_{laudo['id']}")

elif page == "Nova Requisição":
    st.header("📤 Nova Requisição de Laudo")

    # Estilo visual: layout limpo, profissional e inputs em MAIÚSCULAS
    st.markdown("""
        <style>
        .nr-block { background: #f8faf8; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; border-left: 4px solid #2e7d32; }
        .nr-preview { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; font-family: 'Segoe UI', sans-serif; font-size: 0.9rem; line-height: 1.5; }
        /* Inputs de texto da requisição: exibição em maiúsculas */
        .main .block-container input[type="text"],
        .main .block-container textarea { text-transform: uppercase; }
        </style>
    """, unsafe_allow_html=True)

    # Mostrar feedback de requisição enviada (no topo, sempre visível)
    if st.session_state.get('requisicao_enviada') and st.session_state.get('requisicao_info'):
        info = st.session_state['requisicao_info']

        # Container destacado para a mensagem de sucesso
        st.success(f"✅ **Requisição enviada com sucesso!** ID: {info['req_id'][:8]}")
        st.info("📝 O veterinário administrador irá analisar e liberar o laudo. Você será notificado quando estiver disponível para download.")

        if st.button("✖️ Fechar", key="close_requisicao_feedback"):
            del st.session_state['requisicao_enviada']
            del st.session_state['requisicao_info']
            st.rerun()

        st.markdown("---")

        # Script para rolar para o topo quando a mensagem aparecer (executa após rerun)
        st.markdown("""
            <script>
                (function() {
                    function scrollToTop() {
                        if (window.parent && window.parent.scrollTo) {
                            window.parent.scrollTo({ top: 0, behavior: 'smooth' });
                        } else if (window.scrollTo) {
                            window.scrollTo({ top: 0, behavior: 'smooth' });
                        }
                    }
                    // Tentar imediatamente
                    scrollToTop();
                    // Tentar após um pequeno delay (após rerun)
                    setTimeout(scrollToTop, 100);
                    setTimeout(scrollToTop, 300);
                })();
            </script>
        """, unsafe_allow_html=True)

    # Inicializar chaves do formulário (evitar KeyError)
    for k in ["nr_paciente", "nr_tutor", "nr_clinica", "nr_especie", "nr_idade", "nr_raca",
              "nr_sexo", "nr_medico_vet", "nr_regiao", "nr_suspeita", "nr_plantao", "nr_historico",
              "nr_tipo_exame", "nr_veterinario_id"]:
        if k not in st.session_state:
            st.session_state[k] = ""
    if "nr_plantao" not in st.session_state or st.session_state["nr_plantao"] == "":
        st.session_state["nr_plantao"] = "Não"
    if "nr_sexo" not in st.session_state or st.session_state["nr_sexo"] == "":
        st.session_state["nr_sexo"] = "Macho"

    def _fmt_dt(x):
        """Formata datetime assumindo que valores sem tz são UTC e converte para GMT-3."""
        from datetime import timezone as _tzmod
        from utils.timezone import utc_to_local
        if x is None:
            return ""
        if isinstance(x, datetime):
            if x.tzinfo is None:
                x = x.replace(tzinfo=_tzmod.utc)
            x_local = utc_to_local(x)
            return x_local.strftime("%d/%m/%Y %H:%M")
        return str(x)[:16]

    user_id = st.session_state.get("user_id")
    rascunhos = requisicao_model.find_by_user(user_id, status="rascunho") if user_id else []
    rascunho_opcoes = [
        "(nenhum)"] + [f"#{r['id'][:8]} – {r.get('paciente', 'Sem nome')} – {_fmt_dt(r.get('created_at'))}" for r in rascunhos]
    rascunho_ids = [None] + [r["id"] for r in rascunhos]
    if "nr_data" not in st.session_state:
        # Usar data local (GMT-3)
        st.session_state["nr_data"] = now().date()

    col_form, = st.columns([1])
    with col_form:
        st.subheader("📋 Dados do Paciente e da Requisição")
        st.caption("Campos com * são obrigatórios. Preencha os dados, anexe as imagens e envie. O laudo será gerado e liberado pelo veterinário administrador.")

        # Carregar rascunho
        if rascunhos:
            idx_sel = st.selectbox(
                "📁 Carregar rascunho",
                range(len(rascunho_opcoes)),
                format_func=lambda i: rascunho_opcoes[i],
                key="nr_rascunho_sel",
            )
            if st.button("🔄 Carregar rascunho", key="nr_load_draft") and idx_sel > 0:
                r = rascunhos[idx_sel - 1]
                for k, v in [("nr_paciente", r.get("paciente", "")), ("nr_tutor", r.get("tutor", "")),
                             ("nr_clinica", r.get("clinica", "")), ("nr_especie", r.get("especie", "")),
                             ("nr_idade", r.get("idade", "")), ("nr_raca", r.get("raca", "")),
                             ("nr_sexo", r.get("sexo", "") or "Macho"), ("nr_medico_vet",
                                                                         r.get("medico_veterinario_solicitante", "")),
                             ("nr_regiao", r.get("regiao_estudo", "")
                              ), ("nr_suspeita", r.get("suspeita_clinica", "")),
                             ("nr_plantao", r.get("plantao", "") or "Não"), ("nr_historico",
                                                                             r.get("historico_clinico", "") or r.get("observacoes", "")),
                             ("nr_tipo_exame", r.get("tipo_exame", "raio-x")), ("nr_veterinario_id", r.get("veterinario_id") or "")]:
                    st.session_state[k] = v or ""
                de = r.get("data_exame") or r.get("created_at")
                if de and hasattr(de, "date"):
                    st.session_state["nr_data"] = de.date()
                else:
                    st.session_state["nr_data"] = now().date()
                st.session_state["nr_draft_id"] = r["id"]
                st.rerun()

        paciente = st.text_input("🐾 Nome do Paciente *",
                                 value=st.session_state.get("nr_paciente", ""), key="nr_paciente")
        ESPECIES_OPCOES = ["", "Canino", "Felino", "Ave", "Silvestre"]
        idx_especie = 0
        nr_especie_val = st.session_state.get("nr_especie", "")
        if nr_especie_val in ESPECIES_OPCOES:
            idx_especie = ESPECIES_OPCOES.index(nr_especie_val)
        especie = st.selectbox(
            "🐕 Espécie",
            options=ESPECIES_OPCOES,
            index=idx_especie,
            key="nr_especie",
            format_func=lambda x: "Selecione a espécie" if x == "" else x,
        )
        idade = st.text_input("📅 Idade", value=st.session_state.get("nr_idade", ""), key="nr_idade")
        raca = st.text_input("🏷️ Raça", value=st.session_state.get("nr_raca", ""), key="nr_raca")
        sexo = st.radio("Sexo", ["Macho", "Fêmea"], index=0 if st.session_state.get(
            "nr_sexo") == "Macho" else 1, key="nr_sexo", horizontal=True)
        tutor = st.text_input("👤 Nome do Tutor(a) *",
                              value=st.session_state.get("nr_tutor", ""), key="nr_tutor")

        # Veterinário requisitante: sempre exibir. Se usuário tem clínica, dropdown com veterinários da clínica.
        st.markdown("**👨‍⚕️ Veterinário requisitante**")
        current_user = get_current_user()
        user_clinica_id = (current_user or {}).get("clinica_id")
        clinica = ""
        medico_vet = ""
        veterinario_id_selecionado = ""
        if user_clinica_id:
            clinica_obj = clinica_model.find_by_id(user_clinica_id)
            veterinarios_list = veterinario_model.find_by_clinica(
                user_clinica_id, apenas_ativos=True) if user_clinica_id else []
            clinica = (clinica_obj or {}).get("nome", "")
            nr_vet_id = st.session_state.get("nr_veterinario_id", "")
            vet_escolhido = None
            if nr_vet_id and veterinarios_list:
                vet_escolhido = next(
                    (v for v in veterinarios_list if v.get("id") == nr_vet_id), None)
            if not vet_escolhido and veterinarios_list:
                vet_escolhido = veterinarios_list[0]
            if len(veterinarios_list) == 0:
                medico_vet = "Equipe " + clinica if clinica else ""
                st.caption(
                    f"**Solicitante:** {clinica}. Nenhum veterinário cadastrado nesta clínica; adicione na administração.")
            elif len(veterinarios_list) == 1:
                medico_vet = (vet_escolhido or {}).get("nome", "") or ("Equipe " + clinica)
                veterinario_id_selecionado = (vet_escolhido or {}).get("id", "")
                st.session_state["nr_veterinario_id"] = veterinario_id_selecionado or ""
                st.text_input("Veterinário requisitante", value=medico_vet,
                              disabled=True, key="nr_vet_display_1", label_visibility="collapsed")
                st.caption(
                    f"**Solicitante:** {clinica} – único veterinário cadastrado (preenchido automaticamente).")
            else:
                options_nomes = [
                    v.get("nome", "") or f"Veterinário {i + 1}" for i, v in enumerate(veterinarios_list)]
                idx_sel = 0
                if vet_escolhido:
                    try:
                        idx_sel = next(i for i, v in enumerate(veterinarios_list)
                                       if v.get("id") == vet_escolhido.get("id"))
                    except StopIteration:
                        idx_sel = 0
                sel_idx = st.selectbox(
                    "Escolha o veterinário responsável por esta requisição",
                    range(len(veterinarios_list)),
                    index=idx_sel,
                    format_func=lambda i: options_nomes[i] if i < len(options_nomes) else "",
                    key="nr_vet_select",
                    label_visibility="visible",
                )
                vet_escolhido = veterinarios_list[sel_idx]
                medico_vet = (vet_escolhido or {}).get("nome", "")
                veterinario_id_selecionado = (vet_escolhido or {}).get("id", "")
                st.session_state["nr_veterinario_id"] = veterinario_id_selecionado or ""
                st.caption(
                    f"**Solicitante:** {clinica} · {len(veterinarios_list)} veterinário(s) cadastrado(s).")
        else:
            st.caption(
                "Seu usuário não está vinculado a uma clínica; informe o nome do veterinário abaixo.")
            medico_vet = st.text_input(
                "Nome do veterinário requisitante",
                value=st.session_state.get("nr_medico_vet", ""),
                key="nr_medico_vet",
                label_visibility="collapsed",
            )

        regiao = st.text_input("📍 Região de estudo", value=st.session_state.get(
            "nr_regiao", ""), key="nr_regiao")
        suspeita = st.text_input("🔬 Suspeita clínica", value=st.session_state.get(
            "nr_suspeita", ""), key="nr_suspeita")
        plantao = st.radio("Plantão", ["Sim", "Não"], index=1, key="nr_plantao", horizontal=True)
        tipo_exame = st.selectbox(
            "📋 Tipo de exame *", ["raio-x", "ultrassom"], index=0, key="nr_tipo_exame")
        data_exame = st.date_input("📆 Data", value=st.session_state.get(
            "nr_data", now().date()), key="nr_data")
        historico = st.text_area("📝 Histórico Clínico", value=st.session_state.get(
            "nr_historico", ""), height=120, key="nr_historico")

        st.subheader("📷 Imagens do Exame")
        # Usar chave dinâmica para permitir reset do uploader
        upload_key = f"nr_upload_{st.session_state.get('upload_counter', 0)}"
        uploaded_files = st.file_uploader(
            "Selecione as imagens (JPG, PNG, DICOM). Múltiplas imagens permitidas.",
            type=["jpg", "jpeg", "png", "dcm", "dicom", "bmp", "tiff"],
            accept_multiple_files=True,
            key=upload_key,
        )
        if uploaded_files:
            st.caption(f"✅ {len(uploaded_files)} arquivo(s) anexado(s) ao laudo.")

        # Campos de texto salvos em UPPERCASE (usado nos payloads abaixo)
        def _upper(s):
            return (s or "").strip().upper() if isinstance(s, str) else s

        # Botão enviar requisição
        enviar = st.button("📤 Enviar Requisição", type="primary",
                           key="nr_enviar", use_container_width=True)

        # Botões: Limpar, Salvar rascunho, Enviar
        c1, c2 = st.columns(2)
        with c1:
            salvar_rascunho = st.button(
                "💾 Salvar rascunho", key="nr_rascunho", use_container_width=True)
        with c2:
            limpar = st.button("🗑️ Limpar formulário", key="nr_limpar", use_container_width=True)

        if limpar:
            for k in list(st.session_state.keys()):
                if k.startswith("nr_") and k not in ("nr_rascunho_sel", "nr_load_draft", "nr_limpar", "nr_rascunho", "nr_enviar"):
                    del st.session_state[k]
            # Resetar com data local (GMT-3)
            st.session_state["nr_data"] = now().date()
            st.session_state["nr_plantao"] = "Não"
            st.session_state["nr_sexo"] = "Macho"
            st.session_state["nr_tipo_exame"] = "raio-x"
            # Incrementar contador do uploader para resetar
            st.session_state["upload_counter"] = st.session_state.get("upload_counter", 0) + 1
            st.rerun()

        if salvar_rascunho:
            if not paciente.strip() or not tutor.strip():
                st.error("Para salvar rascunho, preencha pelo menos Nome do Paciente e Nome do Tutor(a).")
            else:
                from utils.timezone import combine_date_local
                draft_id = st.session_state.get("nr_draft_id")
                data_exame_dt = combine_date_local(data_exame) if data_exame else now()
                payload = {
                    "paciente": _upper(paciente), "tutor": _upper(tutor), "clinica": clinica, "tipo_exame": tipo_exame,
                    "especie": especie, "idade": idade, "raca": _upper(raca), "sexo": sexo,
                    "medico_veterinario_solicitante": medico_vet, "regiao_estudo": _upper(regiao),
                    "suspeita_clinica": _upper(suspeita), "plantao": plantao, "historico_clinico": _upper(historico),
                    "observacoes": _upper(historico), "data_exame": data_exame_dt,
                }
                if user_clinica_id:
                    payload["clinica_id"] = user_clinica_id
                    payload["veterinario_id"] = veterinario_id_selecionado or None
                if draft_id:
                    requisicao_model.update(draft_id, {**payload, "imagens": []})
                    st.success("Rascunho atualizado.")
                else:
                    rid = requisicao_model.create(
                        user_id=user_id, imagens=[], status="rascunho",
                        paciente=payload["paciente"], tutor=payload["tutor"], clinica=payload["clinica"],
                        tipo_exame=payload["tipo_exame"], observacoes=payload["observacoes"],
                        especie=payload["especie"], idade=payload["idade"], raca=payload["raca"], sexo=payload["sexo"],
                        medico_veterinario_solicitante=payload["medico_veterinario_solicitante"],
                        regiao_estudo=payload["regiao_estudo"], suspeita_clinica=payload["suspeita_clinica"],
                        plantao=payload["plantao"], historico_clinico=payload["historico_clinico"],
                        data_exame=payload["data_exame"],
                        clinica_id=payload.get("clinica_id"), veterinario_id=payload.get("veterinario_id"),
                    )
                    st.session_state["nr_draft_id"] = rid
                    st.success("Rascunho salvo.")
                st.rerun()

        if enviar:
            if not paciente or not tutor:
                st.error("Preencha o Nome do Paciente e o Nome do Tutor(a).")
            elif not uploaded_files:
                st.error("Selecione ao menos uma imagem do exame.")
            else:
                from config import UPLOADS_DIR
                user_images_dir = os.path.join(UPLOADS_DIR, user_id)
                os.makedirs(user_images_dir, exist_ok=True)
                imagens_paths = []
                for f in uploaded_files:
                    fp = os.path.abspath(os.path.join(user_images_dir, f.name))
                    try:
                        with open(fp, "wb") as out:
                            out.write(f.getbuffer())
                        imagens_paths.append(fp)
                    except Exception as e:
                        log.exception("Erro ao salvar arquivo %s em %s: %s", f.name, fp, e)
                        raise

                from utils.timezone import combine_date_local
                data_exame_dt = combine_date_local(data_exame) if data_exame else now()

                try:
                    req_id = requisicao_model.create(
                        user_id=user_id, imagens=imagens_paths,
                        paciente=_upper(paciente), tutor=_upper(tutor), clinica=clinica, tipo_exame=tipo_exame,
                        observacoes=_upper(historico), especie=especie, idade=idade, raca=_upper(raca), sexo=sexo,
                        medico_veterinario_solicitante=medico_vet, regiao_estudo=_upper(regiao),
                        suspeita_clinica=_upper(suspeita), plantao=plantao, historico_clinico=_upper(historico),
                        data_exame=data_exame_dt, status="pendente",
                        clinica_id=user_clinica_id or None, veterinario_id=veterinario_id_selecionado or None,
                    )
                    # Imagens apenas armazenadas. Laudo é gerado pela IA quando o admin
                    # acessar "Criar/Editar Laudo" (Requisições) ou "Gerar Laudo com IA" (Laudos).
                    st.session_state["requisicao_enviada"] = True
                    st.session_state["requisicao_info"] = {"req_id": req_id, "paciente": paciente}

                    # Limpar formulário completamente
                    for k in list(st.session_state.keys()):
                        if k.startswith("nr_") and k not in ("nr_rascunho_sel", "nr_load_draft", "nr_limpar", "nr_rascunho", "nr_exportar", "nr_enviar"):
                            del st.session_state[k]

                    # Resetar valores padrão
                    st.session_state["nr_data"] = now().date()
                    st.session_state["nr_plantao"] = "Não"
                    st.session_state["nr_sexo"] = "Macho"
                    st.session_state["nr_tipo_exame"] = "raio-x"

                    # Incrementar contador do uploader para forçar reset
                    st.session_state["upload_counter"] = st.session_state.get(
                        "upload_counter", 0) + 1

                    # Rolar para o topo após rerun
                    st.markdown("""
                        <script>
                            setTimeout(function() {
                                window.parent.scrollTo({ top: 0, behavior: 'smooth' });
                            }, 200);
                        </script>
                    """, unsafe_allow_html=True)
                    st.rerun()
                except Exception as e:
                    log.exception("Erro ao criar requisição após upload: %s", e)
                    st.error(f"Erro ao criar requisição: {str(e)}")

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
                            valor_base = exame.get('valor_base', exame.get('valor', 0))
                            acrescimo_plantao = exame.get('acrescimo_plantao', 0.0)
                            valor_total_exame = exame.get('valor', valor_base + acrescimo_plantao)
                            plantao_flag = exame.get('plantao', False)
                            obs = exame.get('observacao', '')
                            linha = f"{idx}. {paciente}"
                            linha += f" · Base: R$ {valor_base:.2f}"
                            if plantao_flag and acrescimo_plantao:
                                linha += f" · Plantão: +R$ {acrescimo_plantao:.2f}"
                            linha += f" · Total: R$ {valor_total_exame:.2f}"
                            if obs:
                                linha += f" · Obs: {obs}"
                            st.write(linha)
                        if len(fatura.get('exames', [])) > 10:
                            st.write(f"... e mais {len(fatura.get('exames', [])) - 10} exame(s)")

                if fatura.get('status') == 'pendente':
                    st.warning("⚠️ Esta fatura está pendente de pagamento.")
