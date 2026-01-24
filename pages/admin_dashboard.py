"""
Dashboard do Administrador
"""
import streamlit as st
from datetime import datetime, timedelta
from auth.auth_utils import get_current_user, clear_session, require_auth
from database.connection import get_db
from database.models import Requisicao, Laudo, User, Fatura
import os
import io
import base64
# PIL.Image será importado lazy quando necessário (evita problemas com Python 3.13)

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

# Verificar autenticação
if not st.session_state.get('authenticated'):
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

    if st.button("🚪 Sair", use_container_width=True):
        clear_session()
        st.switch_page("pages/login.py")

    st.divider()

    # Navegação
    page = st.radio(
        "Navegação",
        ["Requisições", "Laudos", "Usuários", "Financeiro", "Knowledge Base"],
        key="admin_nav"
    )
    
    # Se há uma requisição sendo editada e estamos em outra página, mostrar aviso
    if st.session_state.get('editing_requisicao') and page != "Laudos":
        st.info("💡 **Você tem uma requisição sendo editada.** Acesse a página 'Laudos' no menu acima para continuar a edição.")

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
        search_term = st.text_input("🔍 Buscar (paciente/tutor)")

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
        st.metric("⏳ Pendentes", len(pendentes_req), delta=len(pendentes_req) if not show_all_dates else None, delta_color="off")
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
        search_lower = search_term.lower()
        requisicoes = [
            r for r in requisicoes
            if search_lower in r.get('paciente', '').lower()
            or search_lower in r.get('tutor', '').lower()
        ]

    st.metric("Total de Requisições", len(requisicoes))

    # Lista de requisições
    for req in requisicoes:
        with st.expander(f"📄 Requisição #{req['id'][:8]} - {req.get('paciente', 'Sem nome')} - {req.get('status', 'N/A')}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                st.write(f"**Tipo:** {req.get('tipo_exame', 'N/A')}")
                st.write(f"**Status:** {req.get('status', 'N/A')}")
                st.write(f"**Data:** {req.get('created_at', 'N/A')}")

            with col2:
                # Buscar usuário
                user = user_model.find_by_id(req.get('user_id'))
                if user:
                    st.write(f"**Usuário:** {user.get('nome', user.get('username'))}")
                    st.write(f"**Email:** {user.get('email')}")

                # Verificar se já existe laudo
                laudo = laudo_model.find_by_requisicao(req['id'])
                if laudo:
                    status_laudo = laudo.get('status')
                    if status_laudo == 'pendente':
                        st.warning(f"⏳ Laudo pendente - Aguardando sua revisão!")
                    elif status_laudo == 'liberado':
                        st.success(f"✅ Laudo liberado")
                    else:
                        st.info(f"📝 Laudo: {status_laudo}")
                else:
                    st.warning("⏳ Laudo ainda não foi criado")

            # Observações
            if req.get('observacoes'):
                st.write(f"**Observações:** {req.get('observacoes')}")

            # Imagens (preview)
            if req.get('imagens'):
                st.write(f"**Imagens:** {len(req.get('imagens', []))} arquivo(s)")
                # Aqui poderia mostrar preview das imagens

            # Ações
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                if st.button("📝 Criar/Editar Laudo", key=f"edit_{req['id']}"):
                    # Verificar se já existe laudo
                    laudo_existente = laudo_model.find_by_requisicao(req['id'])

                    if not laudo_existente:
                        # Gerar laudo automaticamente com IA
                        try:
                            with st.spinner("🤖 Gerando laudo com IA..."):
                                imagens_paths = req.get('imagens', [])
                                if imagens_paths:
                                    from ai.analyzer import VetAIAnalyzer, load_images_for_analysis
                                    images = load_images_for_analysis(imagens_paths)
                                    if images:
                                        ai_analyzer = VetAIAnalyzer()
                                        texto_gerado = ai_analyzer.generate_diagnosis(images)
                                        laudo_model.create(
                                            requisicao_id=req['id'],
                                            texto=texto_gerado,
                                            texto_original=texto_gerado,
                                            status="pendente",
                                        )
                                        st.success("✅ Laudo gerado automaticamente com IA!")
                                    else:
                                        st.warning("Nenhuma imagem válida (JPG, PNG, DICOM). Crie o laudo manualmente.")
                        except Exception as e:
                            st.warning(f"⚠️ Erro ao gerar laudo automaticamente: {str(e)}")
                            st.info("Você pode criar o laudo manualmente na página Laudos.")

                    st.session_state['editing_requisicao'] = req['id']
                    # Mostrar mensagem informativa
                    st.info("💡 **Laudo criado/editado!** Acesse a página 'Laudos' no menu lateral para revisar e editar o laudo.")
                    st.rerun()

            with col_btn2:
                if req.get('status') == 'pendente':
                    if st.button("✅ Iniciar Análise", key=f"start_{req['id']}"):
                        requisicao_model.update_status(req['id'], 'em_analise')
                        st.success("Análise iniciada")
                        st.rerun()

            with col_btn3:
                if st.button("🗑️ Rejeitar", key=f"reject_{req['id']}"):
                    requisicao_model.update_status(req['id'], 'rejeitado')
                    st.success("Requisição rejeitada")
                    st.rerun()

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

    # Verificar se está editando uma requisição (vindo da aba Requisições)
    if st.session_state.get('editing_requisicao'):
        req_id = st.session_state['editing_requisicao']
        req = requisicao_model.find_by_id(req_id)

        if req:
            st.subheader(f"Editando Laudo - Requisição #{req_id[:8]}")

            # Imagens da requisição – visíveis para a veterinária conferir o laudo
            imagens_paths = req.get("imagens", [])
            if imagens_paths:
                try:
                    from ai.analyzer import load_images_for_analysis
                    imgs = load_images_for_analysis(imagens_paths)
                    if imgs:
                        st.subheader("🖼️ Imagens para conferência do laudo")
                        ncols = min(3, len(imgs))
                        cols = st.columns(ncols)
                        for i, img in enumerate(imgs):
                            with cols[i % ncols]:
                                st.image(img, use_container_width=True, caption=f"Imagem {i + 1}")
                        st.markdown("---")
                    else:
                        st.warning("Não foi possível carregar as imagens para exibição.")
                except Exception as e:
                    st.warning(f"Erro ao exibir imagens: {e}")
            else:
                st.info("Nenhuma imagem associada a esta requisição.")

            # Buscar laudo existente ou criar novo
            laudo = laudo_model.find_by_requisicao(req_id)

            if not laudo:
                # Gerar laudo inicial com IA
                if st.button("🤖 Gerar Laudo com IA"):
                    with st.spinner("Gerando laudo com IA..."):
                        try:
                            imagens_paths = req.get('imagens', [])
                            if not imagens_paths:
                                st.error("Nenhuma imagem encontrada na requisição")
                            else:
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
                                    laudo = laudo_model.find_by_id(laudo_id)
                                    st.success("Laudo gerado com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível carregar as imagens (JPG, PNG, DICOM)")
                        except Exception as e:
                            st.error(f"Erro ao gerar laudo: {str(e)}")
                            import traceback
                            st.exception(e)

                # Se ainda não tem laudo, criar um placeholder
                if not laudo:
                    texto_inicial = "Clique em 'Gerar Laudo com IA' para gerar o laudo automaticamente, ou edite manualmente abaixo."

                    laudo_id = laudo_model.create(
                        requisicao_id=req_id,
                        texto=texto_inicial,
                        texto_original=texto_inicial,
                        status="pendente"
                    )
                    laudo = laudo_model.find_by_id(laudo_id)

            # Editor de laudo
            texto_editado = st.text_area(
                "Editar Laudo",
                value=laudo.get('texto', ''),
                height=400
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("💾 Salvar", use_container_width=True):
                    laudo_model.update(laudo['id'], {"texto": texto_editado})
                    st.success("Laudo salvo!")
                    st.rerun()

            with col2:
                if st.button("✅ Validar", use_container_width=True):
                    user = get_current_user()
                    laudo_model.validate(laudo['id'], user['id'])
                    requisicao_model.update_status(req_id, 'validado')
                    try:
                        from vector_db.vector_store import VectorStore
                        vector_store = VectorStore()
                        vector_store.add_laudo(
                            laudo['id'],
                            texto_editado,
                            metadata={
                                'paciente': req.get('paciente'),
                                'tipo_exame': req.get('tipo_exame'),
                                'status': 'validado'
                            }
                        )
                        st.success("Laudo validado e adicionado ao banco de aprendizado!")
                    except Exception as vec_err:
                        st.success("Laudo validado!")
                        st.warning(
                            f"Não foi possível adicionar ao banco vetorial (chromadb/rpds): {vec_err!s}. "
                            "Execute `just fix-rpds` ou use Python 3.11/3.12."
                        )
                    st.rerun()

            with col3:
                if st.button("📤 Liberar", use_container_width=True):
                    laudo_model.release(laudo['id'])
                    requisicao_model.update_status(req_id, 'liberado')
                    st.success(
                        "✅ Laudo liberado para o usuário! Ele poderá visualizar e fazer download agora.")
                    st.balloons()
                    st.rerun()

            with col4:
                if st.button("❌ Cancelar", use_container_width=True):
                    del st.session_state['editing_requisicao']
                    st.rerun()

            # Mostrar informações da requisição
            with st.expander("ℹ️ Informações da Requisição"):
                st.write(f"**Paciente:** {req.get('paciente')}")
                st.write(f"**Tutor:** {req.get('tutor')}")
                st.write(f"**Tipo:** {req.get('tipo_exame')}")
        else:
            st.error("Requisição não encontrada")
            del st.session_state['editing_requisicao']
    else:
        # Lista de laudos
        st.subheader("📋 Lista de Laudos")

        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Filtrar por Status",
                ["Todos", "pendente", "validado", "liberado", "rejeitado"],
                help="Laudos pendentes precisam de revisão e liberação"
            )
        with col2:
            search_term = st.text_input("🔍 Buscar (paciente/tutor)")

        status = None if status_filter == "Todos" else status_filter
        laudos = laudo_model.find_all(status=status)

        # Aplicar busca
        if search_term:
            search_lower = search_term.lower()
            laudos_filtrados = []
            for laudo in laudos:
                req = requisicao_model.find_by_id(laudo.get('requisicao_id'))
                if req:
                    if (search_lower in req.get('paciente', '').lower()
                            or search_lower in req.get('tutor', '').lower()):
                        laudos_filtrados.append(laudo)
            laudos = laudos_filtrados

        # Ordenar: pendentes primeiro
        laudos_ordenados = sorted(laudos, key=lambda x: (
            0 if x.get('status') == 'pendente' else
            1 if x.get('status') == 'validado' else 2
        ))

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

                    # Ações
                    col_btn1, col_btn2, col_btn3 = st.columns(3)

                    with col_btn1:
                        if st.button("✏️ Editar/Revisar", key=f"edit_laudo_{laudo['id']}", use_container_width=True):
                            st.session_state['editing_requisicao'] = laudo.get('requisicao_id')
                            st.rerun()

                    with col_btn2:
                        if laudo.get('status') == 'pendente':
                            if st.button("✅ Validar", key=f"validate_{laudo['id']}", use_container_width=True):
                                user = get_current_user()
                                laudo_model.validate(laudo['id'], user['id'])
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
