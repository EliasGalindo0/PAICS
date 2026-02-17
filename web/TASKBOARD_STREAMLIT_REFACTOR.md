# Taskboard: Refatoração Streamlit → Next.js

Funcionalidades do Streamlit ainda não implementadas ou incompletas no Next.js.

---

## ✅ Já Implementado

- Login, alteração de senha obrigatória (primeiro acesso)
- Clínicas e usuários (cadastro, edição, filtros, veterinários)
- Exames admin (lista, filtros, abrir, gerar laudo)
- Exame admin detalhe (seleção de imagens, zoom, edição laudo: liberar/corrigir/cancelar)
- Nova requisição (admin e user) com clínica/veterinário pré-preenchidos
- Minhas faturas (user) – lista e métricas
- Financeiro admin (fechamento, faturas)
- Sidebar fixa com ocultar/exibir

---

## 📋 Pendências (ordenadas por prioridade)

### 1. **Rascunhos na Nova Requisição (User)**
- **Streamlit:** Salvar rascunho, carregar rascunho, limpar formulário
- **Next.js:** Não tem rascunhos
- **API:** `POST /requisicoes/rascunho` existe
- **Esforço:** Médio

### 2. **Filtro por data nos Meus Exames (User)**
- **Streamlit:** Filtro por data (padrão: hoje), checkbox "Mostrar todas as datas"
- **Next.js:** Apenas filtro por status
- **API:** `listExames` aceita `start_date` e `end_date`
- **Esforço:** Baixo

### 3. **Notificação de laudos recém liberados (User)**
- **Streamlit:** "🎉 N laudo(s) liberado(s)!" quando há laudos liberados desde última visita
- **Next.js:** Não tem
- **Esforço:** Baixo (precisa armazenar última visita em localStorage)

### 4. **Expansível / lista detalhada nos Meus Exames (User)**
- **Streamlit:** Expander por exame com dados completos, observações, adicionar obs, baixar PDF inline
- **Next.js:** Tabela simples + link para página de detalhe
- **Esforço:** Médio – pode manter tabela + link para detalhe (já existe), mas faltam observações inline na listagem

### 5. **Detalhe do exame User: visualizar imagens e zoom**
- **Streamlit:** Laudo liberado mostra texto + botão PDF
- **Next.js:** Similar, mas sem preview de imagens
- **Esforço:** Baixo – adicionar galeria de imagens com zoom na página user/exames/[id]

### 6. **Admin Exames: filtro por data e ordenação**
- **Streamlit:** Filtro data (hoje por padrão), "Mostrar todas", ordenar por Data/Status/Clínica/Paciente, visualização Rápida/Detalhada
- **Next.js:** Tem filtro status, tipo, busca – falta data e ordenação
- **API:** Já suporta start_date, end_date
- **Esforço:** Baixo

### 7. **Admin Exames: geração em massa**
- **Streamlit:** Botão "Gerar laudos em massa (N pendente(s))" com barra de progresso
- **Next.js:** Gerar um por um na lista
- **API:** Pode precisar de endpoint ou chamar gerar-laudo em loop
- **Esforço:** Médio

### 8. **Admin Financeiro: valor por exame e plantão**
- **Streamlit:** Campos "Valor por Exame (R$)", "Acréscimo Plantão (R$)" antes de gerar fechamento
- **Next.js:** Não exibe/permite configurar
- **API:** Verificar se fechamento aceita esses parâmetros
- **Esforço:** Médio

### 9. **Admin Financeiro: marcar fatura como paga / cancelar**
- **Streamlit:** Botões para marcar paga e cancelar fatura
- **Next.js:** Lista faturas mas não tem ações
- **Esforço:** Baixo

### 10. **Admin Clínicas: detalhe do usuário**
- **Streamlit:** Página de detalhe do usuário com estatísticas, desativar/ativar, excluir, definir senha temporária
- **Next.js:** Verificar se clinicas page tem isso
- **Esforço:** Médio

### 11. **User Faturas: expandir detalhes com exames**
- **Streamlit:** Expander com lista de exames da fatura (paciente, valor base, plantão, total)
- **Next.js:** Card simples sem detalhes dos exames
- **Esforço:** Baixo

### 12. **Knowledge Base e Aprendizado (Admin)** ✅
- **Streamlit:** Seção completa: adicionar PDF/prompt/orientação, buscar, listar, sistema de aprendizado com métricas
- **Next.js:** Implementado em `/admin/knowledge-base` com abas: Adicionar, Buscar, Listar, Sistema de Aprendizado
- **API:** Endpoints criados: listar, buscar, adicionar PDF/prompt/orientação, excluir, learning/stats
- **Esforço:** Alto

### 13. **Alternar tema claro/escuro**
- **Streamlit:** theme_toggle_button na sidebar
- **Next.js:** Não tem
- **Esforço:** Baixo

---

## Ordem sugerida de implementação

1. Rascunhos na Nova Requisição (User)
2. Filtro por data nos Meus Exames
3. Notificação laudos recém liberados
4. Admin Financeiro: marcar paga / cancelar fatura
5. Admin Exames: filtro data e ordenação
6. Detalhe exame User: imagens com zoom
7. Admin Financeiro: valor exame e plantão
8. Admin Exames: geração em massa
9. User Faturas: detalhes dos exames
10. Alternar tema claro/escuro
11. Admin Clínicas: detalhe do usuário
12. Knowledge Base (se API existir)
