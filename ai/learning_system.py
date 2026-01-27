"""
Sistema de aprendizado contínuo para geração de laudos
"""
import os
from typing import List, Optional, Dict, Tuple
from PIL import Image
from database.connection import get_db
from database.models import Laudo, Requisicao, LearningHistory
from vector_db.vector_store import VectorStore
from ai.analyzer import VetAIAnalyzer
from ai.local_model import get_local_model, LocalModelInterface


class LearningSystem:
    """Sistema de aprendizado contínuo para geração de laudos"""
    
    def __init__(self):
        self.db = get_db()
        self.laudo_model = Laudo(self.db.laudos)
        self.requisicao_model = Requisicao(self.db.requisicoes)
        self.learning_model = LearningHistory(self.db.learning_history)
        self.vector_store = VectorStore()
        self.external_analyzer = VetAIAnalyzer()
        self.local_model: Optional[LocalModelInterface] = get_local_model()
        
        # Configurações
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
        self.min_rating_for_local = int(os.getenv("MIN_RATING_FOR_LOCAL", "3"))
        self.use_external_fallback = os.getenv("USE_EXTERNAL_FALLBACK", "true").lower() == "true"
    
    def generate_laudo(
        self, 
        images: List[Image.Image],
        paciente_info: Dict[str, str],
        requisicao_id: str
    ) -> Tuple[str, Dict]:
        """
        Gera laudo usando sistema de aprendizado contínuo
        
        Returns:
            Tuple[texto_gerado, metadata]
            metadata contém: modelo_usado, usado_api_externa, similaridade_casos, casos_similares
        """
        # 1. Buscar casos similares
        similar_cases = self._find_similar_cases(paciente_info)
        similarity_score = similar_cases.get("similarity", 0.0) if similar_cases else 0.0
        
        # 2. Decidir qual modelo usar
        use_local, use_external = self._decide_model_usage(similar_cases, similarity_score)
        
        metadata = {
            "modelo_usado": "híbrido" if (use_local and use_external) else ("local" if use_local else "api_externa"),
            "usado_api_externa": use_external,
            "similaridade_casos": similarity_score,
            "casos_similares": similar_cases.get("case_ids", []) if similar_cases else []
        }
        
        # 3. Gerar laudo
        texto_gerado = ""
        
        if use_local and self.local_model:
            try:
                # Tentar gerar com modelo local primeiro
                prompt = self._build_prompt(paciente_info, similar_cases)
                texto_gerado = self.local_model.generate_text(prompt, images)
                
                # Se usar híbrido, validar/refinar com API externa
                if use_external and self.use_external_fallback:
                    texto_gerado = self._refine_with_external(texto_gerado, images, paciente_info)
            except Exception as e:
                # Fallback para API externa se local falhar
                if use_external or self.use_external_fallback:
                    texto_gerado = self.external_analyzer.generate_diagnosis(images, paciente_info)
                    metadata["usado_api_externa"] = True
                    metadata["modelo_usado"] = "api_externa"
                else:
                    raise RuntimeError(f"Modelo local falhou e fallback desabilitado: {str(e)}")
        else:
            # Usar apenas API externa
            texto_gerado = self.external_analyzer.generate_diagnosis(images, paciente_info)
        
        return texto_gerado, metadata
    
    def _find_similar_cases(self, paciente_info: Dict[str, str]) -> Optional[Dict]:
        """
        Busca casos similares usando contexto e embeddings
        
        Returns:
            Dict com similarity, case_ids, cases_data ou None
        """
        # 1. Buscar por contexto similar (especie, raca, região, suspeita)
        contexto = {
            "especie": paciente_info.get("especie", ""),
            "raca": paciente_info.get("raca", ""),
            "regiao_estudo": paciente_info.get("regiao_estudo", ""),
            "suspeita_clinica": paciente_info.get("suspeita_clinica", "")
        }
        
        similar_cases = self.learning_model.find_similar_context(
            contexto, 
            min_rating=self.min_rating_for_local,
            limit=5
        )
        
        if not similar_cases:
            return None
        
        # 2. Buscar também no vector store usando embeddings
        query_text = self._build_search_query(paciente_info)
        vector_results = self.vector_store.search_similar(query_text, n_results=3)
        
        # 3. Combinar resultados e calcular similaridade média
        case_ids = []
        cases_data = []
        
        for case in similar_cases:
            case_ids.append(case.get("laudo_id"))
            cases_data.append({
                "laudo_id": case.get("laudo_id"),
                "rating": case.get("rating"),
                "texto": case.get("texto_final", ""),
                "contexto": case.get("contexto", {})
            })
        
        # Calcular similaridade baseada em:
        # - Match exato de espécie + raça + região = 0.8
        # - Match parcial = 0.5
        # - Vector similarity = 0.2 adicional
        similarity = 0.0
        if similar_cases:
            # Similaridade baseada em contexto
            exact_matches = sum(1 for case in similar_cases 
                              if case.get("contexto", {}).get("especie") == contexto.get("especie")
                              and case.get("contexto", {}).get("raca") == contexto.get("raca"))
            if exact_matches > 0:
                similarity = 0.8
            elif len(similar_cases) > 0:
                similarity = 0.5
            
            # Adicionar similaridade do vector store
            if vector_results and len(vector_results) > 0:
                avg_vector_sim = 1.0 - (sum(r.get("distancia", 1.0) for r in vector_results) / len(vector_results))
                similarity = min(1.0, similarity + (avg_vector_sim * 0.2))
        
        return {
            "similarity": similarity,
            "case_ids": case_ids,
            "cases_data": cases_data,
            "vector_results": vector_results
        }
    
    def _decide_model_usage(self, similar_cases: Optional[Dict], similarity_score: float) -> Tuple[bool, bool]:
        """
        Decide se deve usar modelo local, API externa ou ambos
        
        Returns:
            Tuple[use_local, use_external]
        """
        use_local = False
        use_external = False
        
        # Se não há modelo local disponível, usar apenas externo
        if not self.local_model or not self.local_model.is_available():
            return False, True
        
        # Se há casos similares com alta similaridade e rating alto
        if similar_cases and similarity_score >= self.similarity_threshold:
            # Verificar se há casos com rating 5
            has_high_rating = any(
                case.get("rating", 0) >= 5 
                for case in similar_cases.get("cases_data", [])
            )
            
            if has_high_rating:
                # Usar apenas local se confiança alta
                use_local = True
                use_external = False
            else:
                # Usar local + validar com externo
                use_local = True
                use_external = True
        else:
            # Caso novo ou baixa similaridade: usar API externa
            use_local = False
            use_external = True
        
        return use_local, use_external
    
    def _build_prompt(self, paciente_info: Dict[str, str], similar_cases: Optional[Dict] = None) -> str:
        """Constrói prompt para modelo local incluindo casos similares"""
        base_prompt = f"""
Você é um radiologista veterinário especialista analisando imagens diagnósticas. 
Gere um laudo técnico completo em português (Brasil).

CONTEXTO DO PACIENTE:
- Espécie: {paciente_info.get("especie", "Não informado")}
- Raça: {paciente_info.get("raca", "Não informado")}
- Idade: {paciente_info.get("idade", "Não informado")}
- Sexo: {paciente_info.get("sexo", "Não informado")}
- Histórico Clínico: {paciente_info.get("historico_clinico", "Não informado")}
- Suspeita Clínica: {paciente_info.get("suspeita_clinica", "Não informado")}
- Região de Estudo: {paciente_info.get("regiao_estudo", "Não informado")}
"""
        
        # Adicionar casos similares como referência
        if similar_cases and similar_cases.get("cases_data"):
            base_prompt += "\n\nCASOS SIMILARES APROVADOS (use como referência):\n"
            for i, case in enumerate(similar_cases["cases_data"][:3], 1):
                base_prompt += f"\n--- Caso {i} (Rating: {case.get('rating', 'N/A')}) ---\n"
                base_prompt += f"{case.get('texto', '')[:500]}...\n"
        
        base_prompt += """
ESTRUTURA DO LAUDO (OBRIGATÓRIA):

**Descrição dos Achados:**
[Descrição detalhada e sistemática das estruturas visíveis]

**Impressão Diagnóstica:**
[Impressão diagnóstica baseada nos achados]

**Conclusão:**
[Resumo conciso dos principais achados]

**Recomendações:**
[Sugestões de exames adicionais ou acompanhamento se necessário]

IMPORTANTE: Sua resposta DEVE começar imediatamente com "**Descrição dos Achados:**"
Use terminologia médica veterinária profissional em português.
"""
        
        return base_prompt
    
    def _build_search_query(self, paciente_info: Dict[str, str]) -> str:
        """Constrói query para busca vetorial"""
        parts = []
        if paciente_info.get("especie"):
            parts.append(f"espécie {paciente_info['especie']}")
        if paciente_info.get("raca"):
            parts.append(f"raça {paciente_info['raca']}")
        if paciente_info.get("regiao_estudo"):
            parts.append(f"região {paciente_info['regiao_estudo']}")
        if paciente_info.get("suspeita_clinica"):
            parts.append(paciente_info["suspeita_clinica"])
        
        return " ".join(parts)
    
    def _refine_with_external(self, texto_local: str, images: List[Image.Image], 
                             paciente_info: Dict[str, str]) -> str:
        """Refina texto gerado localmente usando API externa"""
        # Prompt para refinar
        refine_prompt = f"""
Você é um radiologista veterinário revisando um laudo gerado por um modelo local.

LAUDO GERADO LOCALMENTE:
{texto_local}

CONTEXTO DO PACIENTE:
- Espécie: {paciente_info.get("especie", "Não informado")}
- Raça: {paciente_info.get("raca", "Não informado")}
- Idade: {paciente_info.get("idade", "Não informado")}
- Histórico: {paciente_info.get("historico_clinico", "Não informado")}
- Suspeita: {paciente_info.get("suspeita_clinica", "Não informado")}
- Região: {paciente_info.get("regiao_estudo", "Não informado")}

TAREFA: Revise o laudo acima analisando as imagens. Mantenha a estrutura se estiver correta, 
mas corrija erros, adicione detalhes importantes que possam estar faltando, e melhore a precisão diagnóstica.

Sua resposta DEVE começar imediatamente com "**Descrição dos Achados:**"
"""
        
        try:
            # Usar API externa para refinar
            refined = self.external_analyzer.generate_diagnosis(images, paciente_info)
            # Por enquanto, retornar o refinado (poderia fazer merge inteligente)
            return refined
        except Exception:
            # Se falhar, retornar o original
            return texto_local
    
    def save_learning_data(
        self, 
        laudo_id: str, 
        requisicao_id: str,
        contexto: Dict[str, str],
        texto_gerado: str,
        texto_final: str,
        rating: int,
        metadata: Dict
    ) -> str:
        """
        Salva dados de aprendizado após laudo ser aprovado/editado
        
        Returns:
            ID do registro de aprendizado
        """
        # Salvar no learning history
        history_id = self.learning_model.create(
            laudo_id=laudo_id,
            requisicao_id=requisicao_id,
            contexto=contexto,
            texto_gerado=texto_gerado,
            texto_final=texto_final,
            rating=rating,
            modelo_usado=metadata.get("modelo_usado", "api_externa"),
            usado_api_externa=metadata.get("usado_api_externa", True),
            similaridade_casos=metadata.get("similaridade_casos"),
            casos_similares=metadata.get("casos_similares", [])
        )
        
        # Adicionar ao vector store se rating >= 3
        if rating >= 3:
            self.vector_store.add_laudo(
                laudo_id=laudo_id,
                texto=texto_final,
                metadata={
                    "especie": contexto.get("especie", ""),
                    "raca": contexto.get("raca", ""),
                    "regiao_estudo": contexto.get("regiao_estudo", ""),
                    "suspeita_clinica": contexto.get("suspeita_clinica", ""),
                    "rating": rating
                }
            )
        
        return history_id
    
    def get_statistics(self) -> Dict:
        """Retorna estatísticas do sistema de aprendizado"""
        return self.learning_model.get_statistics()
