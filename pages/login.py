"""
Página de Login
"""
from utils.logo import display_logo_centered
from utils.theme import apply_custom_theme
import streamlit as st
from auth.auth_utils import login_user, verify_and_refresh_session
from database.connection import init_db

st.set_page_config(
    page_title="Login - PAICS",
    page_icon="🔐",
    layout="centered",
    menu_items=None
)

# Aplicar tema customizado
apply_custom_theme()

# Ocultar menu de navegação de páginas e reduzir margem superior
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    /* Remover header superior */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* Reduzir margem superior para compensar o logo */
    .main .block-container {
        padding-top: 0.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)


# Inicializar banco de dados
try:
    init_db()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    st.stop()

# Função para carregar tokens do localStorage


def load_tokens_from_localstorage():
    """Carrega tokens do localStorage e coloca no session_state"""
    # Verificar se já temos tokens
    if st.session_state.get('access_token') and st.session_state.get('refresh_token'):
        return True

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
                    # Se falhar, tentar usar diretamente
                    access_token = access_token_b64
                    refresh_token = refresh_token_b64
            else:
                access_token = access_token_b64
                refresh_token = refresh_token_b64

            st.session_state['access_token'] = access_token
            st.session_state['refresh_token'] = refresh_token
            st.query_params.clear()
            # Não fazer rerun aqui - deixar o fluxo continuar para verificar a sessão
            return True

    # Se não temos tokens e não há query params, tentar carregar do localStorage via JavaScript
    st.markdown("""
        <script>
        (function() {
            // Verificar se já estamos processando auto_login para evitar loop
            const url = new URL(window.location);
            if (url.searchParams.has('auto_login')) {
                return; // Já estamos processando
            }
            
            const accessToken = localStorage.getItem('paics_access_token');
            const refreshToken = localStorage.getItem('paics_refresh_token');
            
            if (accessToken && refreshToken) {
                // Codificar tokens em base64 para evitar problemas com caracteres especiais na URL
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
    return False


# Tentar carregar tokens do localStorage
if load_tokens_from_localstorage():
    # Verificar se há tokens válidos (auto-login)
    if verify_and_refresh_session():
        # Limpar query params e redirecionar
        if st.session_state.get('role') == 'admin':
            st.switch_page("pages/admin_dashboard.py")
        else:
            st.switch_page("pages/user_dashboard.py")

# Se já estiver autenticado, redirecionar
if st.session_state.get('authenticated'):
    if st.session_state.get('role') == 'admin':
        st.switch_page("pages/admin_dashboard.py")
    else:
        st.switch_page("pages/user_dashboard.py")

# Exibir logo
display_logo_centered(width=250)

st.title("🔐 Login - PAICS")
st.markdown("Sistema de Análise de Imagens Veterinárias")

st.info("ℹ️ **Acesso Restrito:** Apenas administradores podem criar contas. Entre em contato com o administrador do sistema para obter suas credenciais de acesso.")

st.subheader("Entrar")

with st.form("login_form"):
    email_or_username = st.text_input(
        "Email ou Username", placeholder="seu@email.com ou seu_username")
    password = st.text_input("Senha", type="password")
    remember_me = st.checkbox("Lembrar-me (manter conectado por 30 dias)", value=False)
    submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if submit:
        if email_or_username and password:
            success, message, tokens = login_user(
                email_or_username, password, remember_me=remember_me)
            if success:
                # Sempre salvar tokens no session_state
                if tokens.get('access_token') and tokens.get('refresh_token'):
                    st.session_state['access_token'] = tokens['access_token']
                    st.session_state['refresh_token'] = tokens['refresh_token']

                    # Codificar tokens em base64
                    import base64
                    access_token_b64 = base64.b64encode(tokens['access_token'].encode()).decode()
                    refresh_token_b64 = base64.b64encode(tokens['refresh_token'].encode()).decode()

                    # Usar st.components.v1.html para criar iframe e salvar no localStorage da página principal
                    import streamlit.components.v1 as components

                    # Adicionar listener na página principal ANTES do componente
                    st.markdown("""
                        <script>
                        // Listener para receber tokens do iframe via postMessage (fallback)
                        window.addEventListener('message', function(event) {
                            if (event.data && event.data.type === 'saveTokens') {
                                try {
                                    localStorage.setItem('paics_access_token', event.data.access_token);
                                    localStorage.setItem('paics_refresh_token', event.data.refresh_token);
                                    if (event.data.user_id) {
                                        localStorage.setItem('paics_user_id', event.data.user_id);
                                    }
                                } catch(e) {
                                    // Erro silencioso
                                }
                            }
                        });
                        </script>
                    """, unsafe_allow_html=True)

                    # Obter user_id do session_state (deve estar disponível após create_session)
                    user_id = st.session_state.get('user_id', '')
                    if not user_id:
                        # Se não estiver no session_state, buscar do user que foi logado
                        # O user_id foi definido em create_session, então deve estar disponível
                        pass
                    user_id_b64 = base64.b64encode(user_id.encode()).decode() if user_id else ''

                    # Componente HTML que salva no localStorage da página principal
                    components.html(f"""
                        <!DOCTYPE html>
                        <html>
                        <head><meta charset="UTF-8"></head>
                        <body>
                            <script>
                            try {{
                                const at = atob('{access_token_b64}');
                                const rt = atob('{refresh_token_b64}');
                                const uid = '{user_id_b64}' ? atob('{user_id_b64}') : '';
                                
                                // Tentar salvar no localStorage da página principal (window.parent)
                                try {{
                                    // Acessar window.parent.localStorage (página principal do Streamlit)
                                    if (window.parent && window.parent !== window) {{
                                        window.parent.localStorage.setItem('paics_access_token', at);
                                        window.parent.localStorage.setItem('paics_refresh_token', rt);
                                        if (uid) {{
                                            window.parent.localStorage.setItem('paics_user_id', uid);
                                        }}
                                    }} else {{
                                        throw new Error('window.parent não disponível');
                                    }}
                                }} catch(e1) {{
                                    // Fallback: usar postMessage para enviar tokens à página principal
                                    try {{
                                        window.parent.postMessage({{
                                            type: 'saveTokens',
                                            access_token: at,
                                            refresh_token: rt,
                                            user_id: uid
                                        }}, '*');
                                    }} catch(e2) {{
                                        // Último recurso: salvar no localStorage local do iframe
                                        localStorage.setItem('paics_access_token', at);
                                        localStorage.setItem('paics_refresh_token', rt);
                                        if (uid) {{
                                            localStorage.setItem('paics_user_id', uid);
                                        }}
                                    }}
                                }}
                            }} catch(e) {{
                                // Erro silencioso - não afeta o fluxo principal
                            }}
                            </script>
                        </body>
                        </html>
                    """, height=0)

                st.success(message)
                # Não fazer rerun imediatamente - deixar o JavaScript executar
                # O redirecionamento será feito pela verificação de autenticação
                import time
                time.sleep(1.5)  # Delay maior para garantir execução

                # Verificar se os tokens foram salvos antes de redirecionar
                # (isso será feito na próxima renderização)
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Por favor, preencha todos os campos")
