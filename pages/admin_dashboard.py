"""
Dashboard do Administrador
"""
import streamlit as st
from datetime import datetime, timedelta
from auth.auth_utils import get_current_user, clear_session, require_auth
from database.connection import get_db
from database.models import Requisicao, Laudo, User, Fatura
from main import VetAIAnalyzer
from vector_db.vector_store import VectorStore
import os
from PIL import Image
import io
import base64

st.set_page_config(page_title="Dashboard Admin - PAICS", page_icon="👨‍⚕️", layout="wide")

# Verificar autenticação
if not st.session_state.get('authenticated'):
    st.switch_page("pages/login.py")

if st.session_state.get('role') != 'admin':
    st.error("Acesso negado. Esta página é apenas para administradores.")
    st.stop()

# Inicializar componentes
db = get_db()
requisicao_model = Requisicao(db.requisicoes)
laudo_model = Laudo(db.laudos)
user_model = User(db.users)
fatura_model = Fatura(db.faturas)
vector_store = VectorStore()

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

# Página principal baseada na seleção
if page == "Requisições":
    st.header("📋 Requisições de Laudos")

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "pendente", "em_analise", "validado", "liberado", "rejeitado"]
        )
    with col2:
        tipo_filter = st.selectbox(
            "Filtrar por Tipo",
            ["Todos", "raio-x", "ultrassom"]
        )
    with col3:
        search_term = st.text_input("🔍 Buscar (paciente/tutor/clínica)")

    # Buscar requisições
    status = None if status_filter == "Todos" else status_filter
    requisicoes = requisicao_model.find_all(status=status)

    # Aplicar filtros adicionais
    if tipo_filter != "Todos":
        requisicoes = [r for r in requisicoes if r.get('tipo_exame') == tipo_filter]

    if search_term:
        search_lower = search_term.lower()
        requisicoes = [
            r for r in requisicoes
            if search_lower in r.get('paciente', '').lower()
            or search_lower in r.get('tutor', '').lower()
            or search_lower in r.get('clinica', '').lower()
        ]

    st.metric("Total de Requisições", len(requisicoes))

    # Lista de requisições
    for req in requisicoes:
        with st.expander(f"📄 Requisição #{req['id'][:8]} - {req.get('paciente', 'Sem nome')} - {req.get('status', 'N/A')}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")
                st.write(f"**Clínica:** {req.get('clinica', 'N/A')}")
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
                    st.info(f"✅ Laudo já criado (Status: {laudo.get('status')})")
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
                    st.session_state['editing_requisicao'] = req['id']
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

    # Verificar se está editando uma requisição
    if st.session_state.get('editing_requisicao'):
        req_id = st.session_state['editing_requisicao']
        req = requisicao_model.find_by_id(req_id)

        if req:
            st.subheader(f"Editando Laudo - Requisição #{req_id[:8]}")

            # Buscar laudo existente ou criar novo
            laudo = laudo_model.find_by_requisicao(req_id)

            if not laudo:
                # Gerar laudo inicial com IA
                if st.button("🤖 Gerar Laudo com IA"):
                    with st.spinner("Gerando laudo com IA..."):
                        try:
                            # Carregar imagens da requisição
                            imagens_paths = req.get('imagens', [])
                            if not imagens_paths:
                                st.error("Nenhuma imagem encontrada na requisição")
                            else:
                                # Carregar imagens
                                from PIL import Image
                                images = []
                                for img_path in imagens_paths:
                                    if os.path.exists(img_path):
                                        try:
                                            img = Image.open(img_path)
                                            if img.mode != 'RGB':
                                                img = img.convert('RGB')
                                            images.append(img)
                                        except Exception as e:
                                            st.warning(f"Erro ao carregar {img_path}: {e}")

                                if images:
                                    # Gerar laudo com IA
                                    ai_analyzer = VetAIAnalyzer()
                                    texto_gerado = ai_analyzer.generate_diagnosis(images)

                                    # Criar laudo
                                    laudo_id = laudo_model.create(
                                        requisicao_id=req_id,
                                        texto=texto_gerado,
                                        texto_original=texto_gerado,
                                        status="pendente"
                                    )
                                    laudo = laudo_model.find_by_id(laudo_id)
                                    st.success("Laudo gerado com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("Não foi possível carregar as imagens")
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
                    # Adicionar ao banco vetorial
                    vector_store.add_laudo(
                        laudo['id'],
                        texto_editado,
                        metadata={
                            'paciente': req.get('paciente'),
                            'tipo_exame': req.get('tipo_exame'),
                            'status': 'validado'
                        }
                    )
                    requisicao_model.update_status(req_id, 'validado')
                    st.success("Laudo validado e adicionado ao banco de aprendizado!")
                    st.rerun()

            with col3:
                if st.button("📤 Liberar", use_container_width=True):
                    laudo_model.release(laudo['id'])
                    requisicao_model.update_status(req_id, 'liberado')
                    st.success("Laudo liberado para o usuário!")
                    st.rerun()

            with col4:
                if st.button("❌ Cancelar", use_container_width=True):
                    del st.session_state['editing_requisicao']
                    st.rerun()

            # Mostrar informações da requisição
            with st.expander("ℹ️ Informações da Requisição"):
                st.write(f"**Paciente:** {req.get('paciente')}")
                st.write(f"**Tutor:** {req.get('tutor')}")
                st.write(f"**Clínica:** {req.get('clinica')}")
                st.write(f"**Tipo:** {req.get('tipo_exame')}")
        else:
            st.error("Requisição não encontrada")
            del st.session_state['editing_requisicao']
    else:
        # Lista de laudos
        status_filter = st.selectbox(
            "Filtrar por Status",
            ["Todos", "pendente", "validado", "liberado", "rejeitado"]
        )

        status = None if status_filter == "Todos" else status_filter
        laudos = laudo_model.find_all(status=status)

        st.metric("Total de Laudos", len(laudos))

        for laudo in laudos:
            req = requisicao_model.find_by_id(laudo.get('requisicao_id'))
            with st.expander(f"📄 Laudo #{laudo['id'][:8]} - Status: {laudo.get('status')}"):
                if req:
                    st.write(f"**Paciente:** {req.get('paciente', 'N/A')}")
                    st.write(f"**Tutor:** {req.get('tutor', 'N/A')}")

                st.write(f"**Status:** {laudo.get('status')}")
                st.write(f"**Criado em:** {laudo.get('created_at')}")

                # Preview do laudo
                texto_preview = laudo.get('texto', '')[
                    :200] + "..." if len(laudo.get('texto', '')) > 200 else laudo.get('texto', '')
                st.text_area("Preview", texto_preview, height=100, disabled=True)

                if st.button("✏️ Editar", key=f"edit_laudo_{laudo['id']}"):
                    st.session_state['editing_requisicao'] = laudo.get('requisicao_id')
                    st.rerun()

elif page == "Usuários":
    st.header("👥 Gerenciamento de Usuários")

    users = user_model.get_all()
    st.metric("Total de Usuários", len(users))

    for user in users:
        with st.expander(f"👤 {user.get('nome', user.get('username'))} - {user.get('role')}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Username:** {user.get('username')}")
                st.write(f"**Email:** {user.get('email')}")
                st.write(f"**Nome:** {user.get('nome', 'N/A')}")
                st.write(f"**Role:** {user.get('role')}")
                st.write(f"**Ativo:** {'Sim' if user.get('ativo', True) else 'Não'}")

            with col2:
                # Estatísticas do usuário
                reqs = requisicao_model.find_by_user(user['id'])
                laudos = laudo_model.find_by_user(user['id'])

                st.metric("Requisições", len(reqs))
                st.metric("Laudos", len(laudos))

                # Ações
                if user.get('ativo'):
                    if st.button("🚫 Desativar", key=f"deactivate_{user['id']}"):
                        user_model.update(user['id'], {"ativo": False})
                        st.success("Usuário desativado")
                        st.rerun()
                else:
                    if st.button("✅ Ativar", key=f"activate_{user['id']}"):
                        user_model.update(user['id'], {"ativo": True})
                        st.success("Usuário ativado")
                        st.rerun()

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
