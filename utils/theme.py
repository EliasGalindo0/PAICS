"""
Utilitário para aplicar tema customizado baseado no logo
"""
import streamlit as st


def get_theme_mode() -> str:
    """Retorna o modo do tema atual (light ou dark)"""
    return st.session_state.get('theme_mode', 'light')


def toggle_theme():
    """Alterna entre tema claro e escuro"""
    current = get_theme_mode()
    st.session_state['theme_mode'] = 'dark' if current == 'light' else 'light'
    st.rerun()


def apply_custom_theme():
    """
    Aplica tema customizado via CSS para harmonizar com o logo
    Cores baseadas em tons profissionais de azul/verde (comum em logos veterinários)
    Suporta modo claro e escuro
    """
    theme_mode = get_theme_mode()

    if theme_mode == 'dark':
        # Tema escuro (r""" para que \s etc. no JS sejam literais, sem SyntaxWarning)
        css = r"""
    <style>
    /* Cores principais do tema escuro */
    :root {
        --primary-color: #64b5f6;
        --primary-dark: #42a5f5;
        --primary-light: #90caf9;
        --secondary-color: #66bb6a;
        --secondary-dark: #4caf50;
        --accent-color: #26c6da;
        --background-light: #1e1e1e;
        --background-main: #121212;
        --text-primary: #e0e0e0;
        --text-secondary: #b0b0b0;
        --success-color: #66bb6a;
        --warning-color: #ffa726;
        --error-color: #ef5350;
        --border-color: #424242;
        --card-background: #1e1e1e;
    }
    
    /* Background principal */
    .main {
        background-color: var(--background-main) !important;
    }
    
    .stApp {
        background-color: var(--background-main) !important;
    }
    
    .block-container {
        background-color: var(--background-main) !important;
        box-shadow: none !important;
        border: none !important;
    }

    /* Header no modo escuro: mesma cor do fundo, sem sombra/borda */
    header[data-testid="stHeader"] {
        background-color: var(--background-main) !important;
        box-shadow: none !important;
        border: none !important;
    }
    
    /* Header/Sidebar: manter comportamento padrão do Streamlit */
    
    /* Ajustar margem superior do conteúdo principal */
    .main .block-container {
        padding-top: 0.5rem !important;
    }
    
    /* Remover sombra do logo e containers */
    .element-container {
        box-shadow: none !important;
        background: transparent !important;
    }
    
    /* Remover bordas azuis da sidebar */
    section[data-testid="stSidebar"] {
        border: none !important;
    }
    
    section[data-testid="stSidebar"] > div {
        border-top: none !important;
        border-bottom: none !important;
    }
    
    /* Remover linha azul no topo da sidebar */
    section[data-testid="stSidebar"] > div:first-child,
    section[data-testid="stSidebar"] > div[data-testid="stVerticalBlock"]:first-child,
    section[data-testid="stSidebar"] > div[data-testid="stVerticalBlock"] > div:first-child {
        border-top: none !important;
        border-bottom: none !important;
        border-left: none !important;
        border-right: none !important;
        box-shadow: none !important;
    }
    
    /* Remover qualquer elemento com borda azul na sidebar */
    section[data-testid="stSidebar"] [style*="border"],
    section[data-testid="stSidebar"] [style*="border-top"] {
        border: none !important;
    }

    /* Botões primários */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(100, 181, 246, 0.3);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
        box-shadow: 0 4px 8px rgba(100, 181, 246, 0.4);
        transform: translateY(-2px);
    }

    /* Botões secundários */
    .stButton > button[kind="secondary"] {
        background: var(--card-background);
        color: var(--primary-color) !important;
        border: 2px solid var(--primary-color);
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--background-light);
        border-color: var(--primary-dark);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--card-background) 0%, var(--background-light) 100%);
        border-right: none !important;
        box-shadow: none !important;
    }
    
    section[data-testid="stSidebar"] * {
        color: var(--text-primary);
    }
    
    section[data-testid="stSidebar"] .stButton > button {
        border: none !important;
    }

    /* Títulos */
    h1, h2, h3 {
        color: var(--text-primary) !important;
    }

    /* Links */
    a {
        color: var(--primary-color) !important;
    }

    /* Success messages */
    .stSuccess {
        background-color: rgba(102, 187, 106, 0.1);
        border-left: 4px solid var(--success-color);
        color: var(--text-primary) !important;
    }

    /* Info messages */
    .stInfo {
        background-color: rgba(100, 181, 246, 0.1);
        border-left: 4px solid var(--primary-color);
        color: var(--text-primary) !important;
    }

    /* Warning messages */
    .stWarning {
        background-color: rgba(255, 167, 38, 0.1);
        border-left: 4px solid var(--warning-color);
        color: var(--text-primary) !important;
    }

    /* Error messages */
    .stError {
        background-color: rgba(239, 83, 80, 0.1);
        border-left: 4px solid var(--error-color);
        color: var(--text-primary) !important;
    }

    /* Inputs e textareas - corrigir cores */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stDateInput > div > div > input {
        border: 2px solid var(--border-color);
        border-radius: 6px;
        background-color: var(--card-background) !important;
        color: var(--text-primary) !important;
    }
    
    /* Textareas disabled (preview) - forçar cor clara */
    .stTextArea > div > div > textarea[disabled],
    textarea[disabled],
    textarea[readonly] {
        color: var(--text-primary) !important;
        background-color: var(--card-background) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
    }
    
    /* Placeholder text */
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-secondary) !important;
        opacity: 0.7;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(100, 181, 246, 0.1);
    }

    /* Selectbox */
    .stSelectbox > div > div {
        border: 2px solid var(--border-color);
        border-radius: 6px;
        background-color: var(--card-background);
        color: var(--text-primary) !important;
    }
    
    .stSelectbox [data-baseweb="select"] {
        color: var(--text-primary) !important;
    }

    /* Menu dropdown aberto - texto escuro em fundo branco */
    [data-baseweb="popover"] [data-baseweb="menu"] {
        background-color: #ffffff !important;
    }
    
    [data-baseweb="popover"] [data-baseweb="menu"] li {
        color: #1a237e !important;
        background-color: #ffffff !important;
    }
    
    [data-baseweb="popover"] [data-baseweb="menu"] li > div,
    [data-baseweb="popover"] [data-baseweb="menu"] li > div > div,
    [data-baseweb="popover"] [data-baseweb="menu"] li > div > div > span {
        color: #1a237e !important;
    }
    
    [data-baseweb="popover"] [data-baseweb="menu"] li:hover,
    [data-baseweb="popover"] [data-baseweb="menu"] li[aria-selected="true"] {
        background-color: #e3f2fd !important;
    }
    
    [data-baseweb="popover"] [data-baseweb="menu"] li:hover > div,
    [data-baseweb="popover"] [data-baseweb="menu"] li:hover > div > div,
    [data-baseweb="popover"] [data-baseweb="menu"] li:hover > div > div > span,
    [data-baseweb="popover"] [data-baseweb="menu"] li[aria-selected="true"] > div,
    [data-baseweb="popover"] [data-baseweb="menu"] li[aria-selected="true"] > div > div,
    [data-baseweb="popover"] [data-baseweb="menu"] li[aria-selected="true"] > div > div > span {
        color: #1565c0 !important;
    }

    /* Texto geral em elementos específicos */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] div {
        color: var(--text-primary) !important;
    }
    
    [data-testid="stText"] {
        color: var(--text-primary) !important;
    }
    
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
    }
    
    .streamlit-expanderContent {
        color: var(--text-primary) !important;
    }
    
    [data-testid="column"] p,
    [data-testid="column"] span,
    [data-testid="column"] div {
        color: var(--text-primary) !important;
    }

    /* Divider */
    hr {
        border-color: var(--primary-light);
        margin: 1.5rem 0;
    }

    /* Radio buttons */
    .stRadio > label {
        color: var(--text-primary) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 0.75rem 1.5rem;
        background-color: var(--background-light);
        color: var(--text-secondary) !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--background-light);
        border-radius: 6px;
        color: var(--text-primary) !important;
    }

    /* Dataframe */
    .dataframe {
        border: 1px solid var(--primary-light);
    }

    .dataframe thead {
        background-color: var(--primary-color);
        color: white;
    }
    
    .dataframe tbody tr {
        background-color: var(--card-background);
        color: var(--text-primary) !important;
    }
    
    .dataframe tbody tr:nth-child(even) {
        background-color: var(--background-light);
    }
    </style>
    <script>
    // Fix cores dinamicamente no modo escuro
    (function() {
        function fixColors() {
            // Fix textareas - SEMPRE forçar cor clara, independente do que estiver definido
            document.querySelectorAll('textarea').forEach(el => {
                // Sempre forçar cor clara, removendo qualquer cor azul
                el.style.setProperty('color', '#e0e0e0', 'important');
                el.style.color = '#e0e0e0';
                
                // Para textareas disabled, também forçar -webkit-text-fill-color
                if (el.disabled || el.readOnly) {
                    el.style.setProperty('-webkit-text-fill-color', '#e0e0e0', 'important');
                    el.style.setProperty('color', '#e0e0e0', 'important');
                }
                
                // Garantir background escuro
                if (!el.style.backgroundColor || el.style.backgroundColor === 'transparent' || 
                    el.style.backgroundColor === 'rgba(0, 0, 0, 0)') {
                    el.style.setProperty('background-color', '#1e1e1e', 'important');
                    el.style.backgroundColor = '#1e1e1e';
                }
                
                // Remover qualquer estilo inline que possa estar definindo cor azul
                if (el.getAttribute('style')) {
                    let style = el.getAttribute('style');
                    // Remover referências a cores azuis
                    style = style.replace(/color\s*:\s*rgb\(30,\s*136,\s*229\)/gi, '');
                    style = style.replace(/color\s*:\s*#1e88e5/gi, '');
                    style = style.replace(/color\s*:\s*#1565c0/gi, '');
                    style = style.replace(/color\s*:\s*#64b5f6/gi, '');
                    style = style.replace(/color\s*:\s*blue/gi, '');
                    style = style.replace(/-webkit-text-fill-color\s*:\s*rgb\(30,\s*136,\s*229\)/gi, '');
                    style = style.replace(/-webkit-text-fill-color\s*:\s*#1e88e5/gi, '');
                    // Adicionar cor clara se não tiver
                    if (!style.includes('color')) {
                        style += '; color: #e0e0e0 !important;';
                    }
                    if (!style.includes('-webkit-text-fill-color')) {
                        style += '; -webkit-text-fill-color: #e0e0e0 !important;';
                    }
                    el.setAttribute('style', style);
                }
            });
            
            // Fix dropdown options
            document.querySelectorAll('[data-baseweb="popover"] [data-baseweb="menu"] li').forEach(li => {
                li.querySelectorAll('span, div').forEach(el => {
                    const color = window.getComputedStyle(el).color;
                    if (color.includes('rgb(224, 224, 224)') || color.includes('rgb(176, 176, 176)')) {
                        el.style.setProperty('color', '#1a237e', 'important');
                    }
                });
            });
        }
        
        // Executar imediatamente
        fixColors();
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fixColors);
        }
        
        // Observar mudanças no DOM
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' || mutation.type === 'attributes') {
                    fixColors();
                }
            });
        });
        
        observer.observe(document.body, { 
            childList: true, 
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class']
        });
        
        // Executar periodicamente para garantir
        setInterval(fixColors, 200);
        
        // Executar quando houver interação
        document.addEventListener('click', function() {
            setTimeout(fixColors, 50);
        });
        
        document.addEventListener('input', function() {
            setTimeout(fixColors, 50);
        });
    })();
    </script>
    """
    else:
        # Tema claro
        css = """
    <style>
    /* Cores principais do tema claro */
    :root {
        --primary-color: #1e88e5;
        --primary-dark: #1565c0;
        --primary-light: #64b5f6;
        --secondary-color: #43a047;
        --secondary-dark: #2e7d32;
        --accent-color: #00acc1;
        --background-light: #f5f9fc;
        --background-main: #ffffff;
        --text-primary: #1a237e;
        --text-secondary: #424242;
        --success-color: #4caf50;
        --warning-color: #ff9800;
        --error-color: #f44336;
        --border-color: #e0e0e0;
        --card-background: #ffffff;
    }

    /* Header/Sidebar: manter comportamento padrão do Streamlit */
    
    /* Ajustar margem superior do conteúdo principal */
    .main .block-container {
        padding-top: 0.5rem !important;
    }
    
    /* Remover sombras e bordas indesejadas */
    .main .block-container {
        background-color: var(--background-main);
        box-shadow: none !important;
        border: none !important;
    }
    
    /* Remover sombra do logo */
    .element-container img {
        box-shadow: none !important;
        background: transparent !important;
    }
    
    /* Remover bordas e sombras de containers */
    [data-testid="stVerticalBlock"] {
        box-shadow: none !important;
    }

    /* Botões primários */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(30, 136, 229, 0.3);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
        box-shadow: 0 4px 8px rgba(30, 136, 229, 0.4);
        transform: translateY(-2px);
    }

    /* Botões secundários */
    .stButton > button[kind="secondary"] {
        background: var(--card-background);
        color: var(--primary-color);
        border: 2px solid var(--primary-color);
    }

    .stButton > button[kind="secondary"]:hover {
        background: var(--background-light);
        border-color: var(--primary-dark);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--card-background) 0%, var(--background-light) 100%);
        border-right: none !important;
        box-shadow: none !important;
    }
    
    /* Remover linha azul no topo da sidebar */
    section[data-testid="stSidebar"] > div:first-child {
        border-top: none !important;
        border-bottom: none !important;
    }
    
    /* Remover qualquer borda ou linha azul na sidebar */
    section[data-testid="stSidebar"] hr {
        border-color: var(--border-color) !important;
        border-width: 1px !important;
    }
    
    section[data-testid="stSidebar"] * {
        color: var(--text-primary);
    }
    
    /* Remover bordas azuis de elementos na sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        border: none !important;
    }

    /* Títulos */
    h1, h2, h3 {
        color: var(--text-primary) !important;
    }

    /* Links */
    a {
        color: var(--primary-color) !important;
    }

    a:hover {
        color: var(--primary-dark) !important;
    }

    /* Success messages */
    .stSuccess {
        background-color: rgba(76, 175, 80, 0.1);
        border-left: 4px solid var(--success-color);
        color: var(--text-primary);
    }

    /* Info messages */
    .stInfo {
        background-color: rgba(30, 136, 229, 0.1);
        border-left: 4px solid var(--primary-color);
        color: var(--text-primary);
    }

    /* Warning messages */
    .stWarning {
        background-color: rgba(255, 152, 0, 0.1);
        border-left: 4px solid var(--warning-color);
        color: var(--text-primary);
    }

    /* Error messages */
    .stError {
        background-color: rgba(244, 67, 54, 0.1);
        border-left: 4px solid var(--error-color);
        color: var(--text-primary);
    }

    /* Cards e containers */
    .element-container {
        border-radius: 8px;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid var(--border-color);
        border-radius: 6px;
        transition: border-color 0.3s ease;
        background-color: var(--card-background);
        color: var(--text-primary) !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(30, 136, 229, 0.1);
    }

    /* Selectbox e outros inputs */
    .stSelectbox > div > div {
        border: 2px solid var(--border-color);
        border-radius: 6px;
        background-color: var(--card-background);
        color: var(--text-primary) !important;
    }

    /* Divider */
    hr {
        border-color: var(--primary-light);
        margin: 1.5rem 0;
    }

    /* Badges e status */
    [data-testid="stMetricValue"] {
        color: var(--text-primary);
    }

    /* Radio buttons */
    .stRadio > label {
        color: var(--text-secondary);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 0.75rem 1.5rem;
        background-color: var(--background-light);
        color: var(--text-secondary);
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--background-light);
        border-radius: 6px;
        color: var(--text-primary);
    }
    
    /* Cards e containers com background */
    .element-container {
        background-color: var(--card-background);
    }
    
    /* Dataframe rows */
    .dataframe tbody tr {
        background-color: var(--card-background);
        color: var(--text-primary);
    }
    
    .dataframe tbody tr:nth-child(even) {
        background-color: var(--background-light);
    }
    
    /* Dataframe */
    .dataframe {
        border: 1px solid var(--primary-light);
    }

    .dataframe thead {
        background-color: var(--primary-color);
        color: white;
    }
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


def theme_toggle_button():
    """Exibe botão para alternar entre tema claro e escuro"""
    theme_mode = get_theme_mode()

    if theme_mode == 'dark':
        icon = "☀️"
    else:
        icon = "🌙"

    if st.button(f"{icon} Tema", key="theme_toggle", use_container_width=True):
        toggle_theme()
