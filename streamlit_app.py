"""
PAICS - Aplicação Streamlit para Análise de Imagens Veterinárias com IA
Sistema completo com autenticação, dashboards e banco de dados vetorial.
"""
import logging

from auth.auth_utils import verify_and_refresh_session
import streamlit as st
from dotenv import load_dotenv

# Configurar logging focado em erros (Railway/produção)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
# Habilitar WARNING+ para loggers do app (evitar INFO de libs)
for _n in ("paics", "paics.api", "paics.db", "paics.state", "auth.auth_utils"):
    logging.getLogger(_n).setLevel(logging.INFO)

# --- Carregar variáveis de ambiente do arquivo .env ---
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="PAICS - Análise de Imagens Veterinárias",
    page_icon="🐾",
    layout="wide"
)

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
            st.query_params.clear()  # Limpar query params após processar
            # Não fazer rerun aqui - deixar o fluxo continuar para verificar a sessão
            return

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

            console.log('🔍 [streamlit_app] Verificando localStorage...');
            console.log('Access token encontrado:', !!accessToken);
            console.log('Refresh token encontrado:', !!refreshToken);

            if (accessToken && refreshToken) {
                console.log('✅ [streamlit_app] Tokens encontrados, redirecionando');
                // Codificar tokens em base64 para evitar problemas com caracteres especiais na URL
                const accessTokenB64 = btoa(accessToken);
                const refreshTokenB64 = btoa(refreshToken);

                url.searchParams.set('auto_login', 'true');
                url.searchParams.set('access_token', accessTokenB64);
                url.searchParams.set('refresh_token', refreshTokenB64);
                url.searchParams.set('encoded', 'true');
                window.location.href = url.toString();
            } else {
                console.log('❌ [streamlit_app] Tokens não encontrados no localStorage');
            }
        })();
        </script>
    """, unsafe_allow_html=True)


# Carregar tokens do localStorage
load_tokens_from_localstorage()

# Verificar e renovar sessão se necessário
if st.session_state.get('access_token') and st.session_state.get('refresh_token'):
    if verify_and_refresh_session():
        # Sessão válida, redirecionar para dashboard apropriado
        if st.session_state.get('role') == 'admin':
            st.switch_page("pages/admin_dashboard.py")
        else:
            st.switch_page("pages/user_dashboard.py")
    else:
        # Tokens inválidos, limpar localStorage e redirecionar para login
        st.markdown("""
        <script>
        localStorage.removeItem('paics_access_token');
        localStorage.removeItem('paics_refresh_token');
        </script>
        """, unsafe_allow_html=True)
        st.switch_page("pages/login.py")
elif not st.session_state.get('authenticated'):
    # Sem tokens e não autenticado, redirecionar para login
    st.switch_page("pages/login.py")
else:
    # Autenticado via sessão antiga (sem tokens), redirecionar para dashboard
    if st.session_state.get('role') == 'admin':
        st.switch_page("pages/admin_dashboard.py")
    else:
        st.switch_page("pages/user_dashboard.py")
