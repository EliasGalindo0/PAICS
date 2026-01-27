# Sistema de Aprendizado Contínuo

## Visão Geral

O sistema de aprendizado contínuo permite que o PAICS aprenda com cada laudo processado, melhorando progressivamente a qualidade e reduzindo custos de API externa.

## Arquitetura

### 1. Modelos Disponíveis

- **Modelo Local**: Ollama, LlamaCPP ou outros modelos locais
- **Modelo Externo**: API do Google Gemini (Claude, GPT, etc.)

### 2. Fluxo de Geração

1. **Primeira tentativa**: Sistema busca casos similares no histórico
2. **Decisão inteligente**: 
   - Se encontrar casos similares com alta similaridade e rating alto → usa modelo local
   - Se não encontrar ou similaridade baixa → usa API externa
   - Modo híbrido: gera com local e valida/refina com API externa
3. **Aprendizado**: Após aprovação, salva o caso para uso futuro

### 3. Sistema de Rating Automático

O sistema calcula automaticamente um rating (1-5) baseado em edições:

- **Rating 5/5**: Laudo aprovado sem edições
  - Texto final idêntico ao texto original gerado
  - Salvo como referência para casos similares
  - Usado para treinar o modelo local

- **Rating 3/5**: Laudo editado parcialmente
  - Pequenas correções feitas pelo admin
  - Similaridade > 70% com original
  - Aprendizado moderado

- **Rating 1/5**: Laudo muito editado ou regenerado
  - Mudanças significativas ou reescrita completa
  - Similaridade < 70% com original
  - Indica que o caso precisa de abordagem diferente

### 4. Busca de Similaridade

O sistema usa duas estratégias para encontrar casos similares:

1. **Busca por Contexto**: 
   - Espécie + Raça + Região + Suspeita Clínica
   - Filtra casos com rating >= 3

2. **Busca Vetorial (Embeddings)**:
   - Usa ChromaDB para busca semântica
   - Encontra casos com significado similar

### 5. Decisão de Modelo

O sistema decide qual modelo usar baseado em:

- **Similaridade de casos**: Threshold configurável (padrão: 0.75)
- **Rating dos casos similares**: Mínimo configurável (padrão: 3)
- **Disponibilidade do modelo local**: Se não disponível, usa API externa

## Configuração

### Variáveis de Ambiente

Adicione ao arquivo `.env`:

```env
# Habilitar modelo local
USE_LOCAL_MODEL=true

# Tipo de modelo (ollama, llamacpp)
LOCAL_MODEL_TYPE=ollama

# Nome do modelo Ollama
OLLAMA_MODEL_NAME=llama3.2

# URL do servidor Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Threshold de similaridade (0.0 a 1.0)
SIMILARITY_THRESHOLD=0.75

# Rating mínimo para usar modelo local (1 a 5)
MIN_RATING_FOR_LOCAL=3

# Usar API externa como fallback
USE_EXTERNAL_FALLBACK=true
```

### Instalação do Ollama

1. Baixe e instale o Ollama: https://ollama.ai
2. Baixe um modelo:
   ```bash
   ollama pull llama3.2
   ```
3. Configure as variáveis de ambiente acima
4. Reinicie o sistema

## Uso

### Geração de Laudo

O sistema funciona automaticamente:

1. Admin clica em "Gerar Laudo com IA"
2. Sistema busca casos similares
3. Decide qual modelo usar
4. Gera o laudo
5. Mostra informações sobre o modelo usado

### Aprovação e Aprendizado

Quando o admin libera um laudo:

1. Sistema calcula rating automaticamente
2. Salva no histórico de aprendizado
3. Adiciona ao banco vetorial (se rating >= 3)
4. Caso fica disponível para casos futuros similares

### Métricas

Acesse a página "Aprendizado" no dashboard admin para ver:

- Total de casos processados
- Taxa de aprovação
- Economia de chamadas à API
- Distribuição de ratings
- Últimos casos aprendidos

## Benefícios

1. **Redução de Custos**: Progressivamente usa menos API externa
2. **Velocidade**: Modelo local é mais rápido
3. **Qualidade**: Aprende com casos aprovados
4. **Personalização**: Adapta-se aos padrões da clínica

## Estrutura de Dados

### LearningHistory

Armazena histórico de aprendizado:
- Contexto do paciente
- Texto gerado vs texto final
- Rating calculado
- Modelo usado
- Casos similares encontrados

### Laudo (campos adicionais)

- `modelo_usado`: "local", "api_externa", "híbrido"
- `usado_api_externa`: boolean
- `similaridade_casos`: float (0.0 a 1.0)
- `rating`: int (1, 3 ou 5)
- `num_edicoes`: int
- `texto_original_gerado`: str
- `historico_edicoes`: list

## Troubleshooting

### Modelo local não está disponível

1. Verifique se o Ollama está rodando:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Verifique se o modelo está instalado:
   ```bash
   ollama list
   ```

3. Verifique as variáveis de ambiente

### Rating não está sendo calculado

- Verifique se o laudo tem `texto_original_gerado` preenchido
- O rating é calculado automaticamente ao liberar o laudo

### Casos similares não estão sendo encontrados

- Verifique se há casos com rating >= 3 no histórico
- Ajuste o `MIN_RATING_FOR_LOCAL` se necessário
- Verifique se o ChromaDB está funcionando

## Desenvolvimento Futuro

- Fine-tuning do modelo local com casos aprovados
- Clustering automático de casos similares
- Sugestões de melhorias baseadas em padrões
- Exportação de dados de aprendizado
