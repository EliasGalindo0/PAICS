# Análise do Sistema de Aprendizado - PAICS

## Visão Geral do Fluxo Atual

### Tabelas Envolvidas

1. **`learning_history`** – Histórico de laudos aprovados para aprendizado
   - Armazena: laudo_id, requisicao_id, contexto, texto_gerado, texto_final, rating, modelo_usado, usado_api_externa
   - Usado para: buscar casos similares (espécie, raça, região) e como referência no prompt do modelo local

2. **`correcoes_laudo`** – Correções feitas pelo admin
   - Armazena: laudo_original, texto_correcao, laudo_corrigido, categoria, contexto, rating
   - Usado para: gerar **alertas** no prompt (ex.: "em casos similares houve erro de lateralidade")

3. **`laudos`** – Laudos com campos de aprendizado
   - texto_original_gerado, num_edicoes, historico_edicoes, rating, regenerado_com_correcoes

4. **ChromaDB (vector_store)** – Embeddings de laudos
   - Adiciona laudos com rating >= 3 para busca vetorial

---

## FALHAS CRÍTICAS IDENTIFICADAS

### 1. `save_learning_data` nunca é chamado

A função `LearningSystem.save_learning_data()` existe mas **não é invocada em nenhum ponto** do código. Consequências:

- **`learning_history` permanece vazio** → o modelo local nunca encontra casos similares
- **Vector store não recebe novos laudos** → busca vetorial não evolui
- O fluxo sempre cai em "caso novo ou baixa similaridade" → usa apenas API externa

**Solução:** Chamar `save_learning_data` quando o laudo é **liberado** (`liberar_laudo`), com os dados do laudo e metadata da geração.

---

### 2. Edição manual não usa `registrar_edicao`

O endpoint `atualizar_laudo` faz apenas `laudo_model.update()`, sem chamar `registrar_edicao()`:

```python
laudo_model.update(laudo["id"], {"texto": body.texto})  # Não atualiza num_edicoes!
```

Consequências:

- `num_edicoes` e `historico_edicoes` não são atualizados
- O rating calculado em `release()` usa `num_edicoes == 0` mesmo quando houve edições
- Laudos editados manualmente podem ser classificados como rating 5 incorretamente

**Solução:** No `atualizar_laudo`, usar `registrar_edicao(laudo_id, body.texto, user["id"])` em vez de `update` direto.

---

### 3. Correções não cruzam com rating da API

- `regenerate_with_corrections` salva em `correcoes_laudo` com **rating fixo 2**
- O rating real do laudo original (da LLM) não é obtido nem usado
- Não há integração: "laudo da API teve baixa qualidade (rating 1 ou 2) + admin corrigiu" deveria ser um sinal forte para aprendizado

**Solução:** Ao regenerar, obter o rating do laudo original (calculado ou da API) e incluí-lo. Priorizar pares (laudo_original ruim + correção) para fine-tuning ou exemplos few-shot.

---

### 4. Correções não enriquecem o prompt do modelo local

O modelo local recebe apenas **alertas genéricos** (ex.: "houve erro de lateralidade em casos similares"), mas **não recebe exemplos concretos** de correções:

- `get_alertas_correcoes` retorna mensagens genéricas
- Não inclui o par (erro → correção) como few-shot: "Antes: X. Correção: Y. Depois: Z"

**Solução:** Incluir no prompt exemplos reais de correções similares:
```
Em caso similar (Canino, Poodle, Tórax):
- Erro no laudo: "fratura em membro direito"
- Correção do especialista: "a lesão está no membro ESQUERDO"
- Laudo corrigido: ...
Use isso para evitar o mesmo erro.
```

---

### 5. Modelo local não faz fine-tuning

O `LocalModelInterface` usa Ollama/LlamaCPP **apenas com prompt** (few-shot no texto). Não há:

- Fine-tuning do modelo com pares (laudo_original, correção)
- Atualização de pesos com base em correcoes_laudo + learning_history
- Processo batch que converte correções em dados de treino

O "aprendizado" atual é só **RAG + prompt engineering** (alertas + casos similares), não aprendizado de modelo.

**Solução (mais complexa):** 
- Implementar job assíncrono que gera dataset de fine-tuning a partir de `correcoes_laudo` (laudo_original, laudo_corrigido, contexto)
- Usar Ollama Modelfile ou ferramenta externa para fine-tuning periódico
- Ou: melhorar drasticamente o few-shot injetando 3–5 exemplos de correções reais por categoria no prompt

---

### 6. `find_similar_context` exige match exato demais

A busca atual usa filtros restritivos:

```python
if contexto.get("especie"):
    query["contexto.especie"] = contexto["especie"]
if contexto.get("raca"):
    query["contexto.raca"] = contexto["raca"]
# ...
```

- Espécie vazia → sem filtro de espécie (pode retornar gatos para cães)
- Match exato de raça pode excluir casos relevantes (ex.: "SRD" vs "Vira-lata")

**Solução:** Usar matching mais flexível (regex, normalização) e priorizar espécie. Permitir fallback quando raça não bate (ex.: mesma espécie + região).

---

### 7. Regeneração sempre usa API externa

Em `regenerate_with_corrections`, o texto é sempre gerado por:

```python
novo_texto = self.external_analyzer.generate_diagnosis_with_corrections(...)
```

O **modelo local nunca é usado** para regeneração, mesmo quando há casos similares e correções no contexto. Ele só entra na geração inicial (`generate_laudo`), e mesmo assim só quando `learning_history` tem dados (o que não acontece hoje).

**Solução:** Na regeneração, decidir entre local e API da mesma forma que em `generate_laudo`, usando correções como few-shot no prompt local.

---

## MELHORIAS RECOMENDADAS (Prioridade)

### Alta prioridade (resolvem o fluxo quebrado)

1. **Chamar `save_learning_data` ao liberar laudo**
   - Em `liberar_laudo`, após `laudo_model.release()`, obter laudo e req atualizados
   - Montar contexto e metadata (modelo_usado, usado_api_externa, similaridade_casos)
   - Chamar `LearningSystem().save_learning_data(...)`

2. **Usar `registrar_edicao` ao atualizar laudo**
   - Trocar `laudo_model.update()` por `laudo_model.registrar_edicao()` em `atualizar_laudo`

### Média prioridade (aprimoram o aprendizado)

3. **Injetar exemplos de correções no prompt**
   - Em `_build_prompt`, buscar 2–3 correções de `correcoes_laudo` por contexto
   - Incluir no prompt: "Evite estes erros (exemplos reais): [laudo_original] → [correção] → [laudo_corrigido]"

4. **Salvar rating original ao registrar correção**
   - Ao criar registro em `correcoes_laudo`, usar o rating do laudo original quando disponível

5. **Permitir modelo local na regeneração**
   - Reutilizar lógica de `generate_laudo` em `regenerate_with_corrections` para decidir local vs API
   - Incluir correções como few-shot no prompt local

### Baixa prioridade (evolução de longo prazo)

6. **Fine-tuning periódico** com pares (laudo_original, laudo_corrigido) de `correcoes_laudo`
7. **Busca por contexto mais flexível** em `find_similar_context`
8. **Dashboard de métricas** (rating médio, correções por categoria, uso do modelo local vs API)

---

## Fluxo Ideal (Após Correções)

```
1. Admin gera laudo
   → LearningSystem.generate_laudo()
   → Busca casos similares (learning_history + vector_store)
   → Se similaridade alta: usa modelo local + alertas de correções
   → Senão: usa API externa

2. Admin edita manualmente
   → atualizar_laudo → registrar_edicao() (num_edicoes++, historico)

3. Admin regenera com correções
   → regenerate_with_corrections()
   → Salva em correcoes_laudo (laudo_original, correção, laudo_corrigido)
   → [MELHORIA] Usar modelo local quando há casos similares

4. Admin libera laudo
   → liberar_laudo() → release() → _calcular_rating()
   → save_learning_data() → learning_history + vector_store (se rating >= 3)
```

---

## Resumo

O sistema de aprendizado está **parcialmente implementado** mas **não conectado** ao fluxo principal. A função que popula `learning_history` e o vector store nunca é chamada, e a edição manual não atualiza os campos necessários para o cálculo de rating. As correções são salvas e usadas apenas como alertas genéricos, não como exemplos concretos no prompt. Para o modelo local aprender de fato, é essencial:

1. Popular `learning_history` ao liberar
2. Corrigir o fluxo de edição manual
3. Enriquecer o prompt com exemplos reais de correções
4. (Opcional) Fine-tuning periódico com dados de correções
