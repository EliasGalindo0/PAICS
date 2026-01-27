"""
Modelos de dados para MongoDB
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from pymongo.collection import Collection


class BaseModel:
    """Classe base para modelos"""

    def __init__(self, collection: Collection):
        self.collection = collection

    def to_dict(self, doc: Dict) -> Dict:
        """Converte documento MongoDB para dict com _id como string"""
        if doc and '_id' in doc:
            doc['id'] = str(doc['_id'])
            del doc['_id']
        return doc

    def from_dict(self, data: Dict) -> Dict:
        """Converte dict para formato MongoDB"""
        if 'id' in data:
            data['_id'] = ObjectId(data['id'])
            del data['id']
        return data


class User(BaseModel):
    """Modelo de usuário"""

    def create(self, username: str, email: str, password_hash: str,
               role: str = "user", nome: str = "", ativo: bool = True,
               primeiro_acesso: bool = True, senha_temporaria: str = None) -> str:
        """Cria um novo usuário"""
        user_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "role": role,  # "admin" ou "user"
            "nome": nome,
            "ativo": ativo,
            "primeiro_acesso": primeiro_acesso,  # Flag para obrigar alteração de senha
            "senha_temporaria": senha_temporaria,  # Senha temporária gerada pelo admin
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(user_data)
        return str(result.inserted_id)

    def find_by_email(self, email: str) -> Optional[Dict]:
        """Busca usuário por email"""
        doc = self.collection.find_one({"email": email})
        return self.to_dict(doc) if doc else None

    def find_by_username(self, username: str) -> Optional[Dict]:
        """Busca usuário por username"""
        doc = self.collection.find_one({"username": username})
        return self.to_dict(doc) if doc else None

    def find_by_id(self, user_id: str) -> Optional[Dict]:
        """Busca usuário por ID"""
        doc = self.collection.find_one({"_id": ObjectId(user_id)})
        return self.to_dict(doc) if doc else None

    def get_all(self, role: Optional[str] = None) -> List[Dict]:
        """Lista todos os usuários, opcionalmente filtrados por role"""
        query = {} if role is None else {"role": role}
        docs = self.collection.find(query)
        return [self.to_dict(doc) for doc in docs]

    def update(self, user_id: str, updates: Dict) -> bool:
        """Atualiza um usuário"""
        updates["updated_at"] = datetime.utcnow()
        result = self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete(self, user_id: str) -> bool:
        """Exclui um usuário"""
        result = self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0


class Session(BaseModel):
    """Modelo de sessão para refresh tokens"""
    
    def create(self, user_id: str, refresh_token: str, device_id: str, 
               device_info: str = "", ip_address: str = "") -> str:
        """Cria uma nova sessão"""
        session_data = {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "device_id": device_id,
            "device_info": device_info,
            "ip_address": ip_address,
            "created_at": datetime.utcnow(),
            "last_used_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30),
            "active": True
        }
        result = self.collection.insert_one(session_data)
        return str(result.inserted_id)
    
    def find_by_refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Busca sessão por refresh token"""
        doc = self.collection.find_one({
            "refresh_token": refresh_token,
            "active": True
        })
        return self.to_dict(doc) if doc else None
    
    def find_by_user(self, user_id: str) -> List[Dict]:
        """Busca todas as sessões ativas de um usuário"""
        docs = self.collection.find({
            "user_id": user_id,
            "active": True
        }).sort("last_used_at", -1)
        return [self.to_dict(doc) for doc in docs]
    
    def update_last_used(self, session_id: str) -> bool:
        """Atualiza timestamp de último uso"""
        result = self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"last_used_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    def deactivate(self, session_id: str) -> bool:
        """Desativa uma sessão específica"""
        result = self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"active": False, "deactivated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    def deactivate_all_user_sessions(self, user_id: str) -> int:
        """Desativa todas as sessões de um usuário (logout de todos os dispositivos)"""
        result = self.collection.update_many(
            {"user_id": user_id, "active": True},
            {"$set": {"active": False, "deactivated_at": datetime.utcnow()}}
        )
        return result.modified_count
    
    def cleanup_expired(self) -> int:
        """Remove sessões expiradas"""
        result = self.collection.delete_many({
            "expires_at": {"$lt": datetime.utcnow()}
        })
        return result.deleted_count


class Requisicao(BaseModel):
    """Modelo de requisição de laudo"""

    def create(self, user_id: str, imagens: List[str],
               paciente: str = "", tutor: str = "", clinica: str = "",
               tipo_exame: str = "raio-x", observacoes: str = "",
               especie: str = "", idade: str = "", raca: str = "", sexo: str = "",
               medico_veterinario_solicitante: str = "", regiao_estudo: str = "",
               suspeita_clinica: str = "", plantao: str = "", historico_clinico: str = "",
               data_exame: Optional[datetime] = None, status: str = "pendente") -> str:
        """Cria uma nova requisição"""
        req_data = {
            "user_id": user_id,
            "imagens": imagens,
            "paciente": paciente,
            "tutor": tutor,
            "clinica": clinica,
            "tipo_exame": tipo_exame,
            "observacoes": observacoes,
            "especie": especie,
            "idade": idade,
            "raca": raca,
            "sexo": sexo,
            "medico_veterinario_solicitante": medico_veterinario_solicitante,
            "regiao_estudo": regiao_estudo,
            "suspeita_clinica": suspeita_clinica,
            "plantao": plantao,
            "historico_clinico": historico_clinico,
            "data_exame": data_exame or datetime.utcnow(),
            "status": status,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(req_data)
        return str(result.inserted_id)

    def find_by_id(self, req_id: str) -> Optional[Dict]:
        """Busca requisição por ID"""
        doc = self.collection.find_one({"_id": ObjectId(req_id)})
        return self.to_dict(doc) if doc else None

    def find_by_user(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Busca requisições de um usuário"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        docs = self.collection.find(query).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def find_all(self, status: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """Lista todas as requisições, opcionalmente filtradas por status e data"""
        query = {}
        if status:
            query["status"] = status
        
        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date
                
        docs = self.collection.find(query).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def update_status(self, req_id: str, status: str) -> bool:
        """Atualiza o status de uma requisição"""
        result = self.collection.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    def update(self, req_id: str, updates: Dict) -> bool:
        """Atualiza uma requisição (ex.: rascunho)"""
        updates["updated_at"] = datetime.utcnow()
        result = self.collection.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": updates}
        )
        return result.modified_count > 0


class Laudo(BaseModel):
    """Modelo de laudo"""

    def create(self, requisicao_id: str, texto: str,
               texto_original: str = "", status: str = "pendente",
               admin_id: Optional[str] = None,
               modelo_usado: Optional[str] = None,
               usado_api_externa: bool = False,
               similaridade_casos: Optional[float] = None) -> str:
        """Cria um novo laudo"""
        laudo_data = {
            "requisicao_id": requisicao_id,
            "texto": texto,
            "texto_original": texto_original,
            "status": status,  # "pendente", "validado", "liberado", "rejeitado"
            "admin_id": admin_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "validado_at": None,
            "liberado_at": None,
            # Campos para aprendizado
            "modelo_usado": modelo_usado,  # "local", "api_externa", "híbrido"
            "usado_api_externa": usado_api_externa,
            "similaridade_casos": similaridade_casos,
            "rating": None,  # Será calculado quando liberado/editado
            "num_edicoes": 0,
            "texto_original_gerado": texto_original or texto,  # Versão original da IA
            "historico_edicoes": []  # Lista de edições com timestamps
        }
        result = self.collection.insert_one(laudo_data)
        return str(result.inserted_id)

    def find_by_id(self, laudo_id: str) -> Optional[Dict]:
        """Busca laudo por ID"""
        doc = self.collection.find_one({"_id": ObjectId(laudo_id)})
        return self.to_dict(doc) if doc else None

    def find_by_requisicao(self, requisicao_id: str) -> Optional[Dict]:
        """Busca laudo por requisição"""
        doc = self.collection.find_one({"requisicao_id": requisicao_id})
        return self.to_dict(doc) if doc else None

    def find_by_user(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Busca laudos de um usuário através das requisições"""
        from database.connection import get_db
        db = get_db()

        # Buscar requisições do usuário
        reqs = list(db.requisicoes.find({"user_id": user_id}))
        req_ids = [str(req["_id"]) for req in reqs]

        if not req_ids:
            return []

        # Buscar laudos dessas requisições
        query = {"requisicao_id": {"$in": req_ids}}
        if status:
            query["status"] = status

        docs = self.collection.find(query).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def find_all(self, status: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """Lista todos os laudos, opcionalmente filtrados por status e data"""
        query = {}
        if status:
            query["status"] = status
        
        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date

        docs = self.collection.find(query).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def update(self, laudo_id: str, updates: Dict) -> bool:
        """Atualiza um laudo"""
        updates["updated_at"] = datetime.utcnow()
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def validate(self, laudo_id: str, admin_id: str) -> bool:
        """Valida um laudo"""
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": {
                "status": "validado",
                "admin_id": admin_id,
                "validado_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0

    def release(self, laudo_id: str, calcular_rating: bool = True) -> bool:
        """Libera um laudo para o usuário e calcula rating automaticamente"""
        laudo = self.find_by_id(laudo_id)
        if not laudo:
            return False
        
        updates = {
            "status": "liberado",
            "liberado_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Calcular rating se solicitado
        if calcular_rating:
            rating = self._calcular_rating(laudo)
            if rating:
                updates["rating"] = rating
        
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    def _calcular_rating(self, laudo: Dict) -> Optional[int]:
        """
        Calcula rating automático baseado em edições:
        - Rating 5: Laudo aprovado sem edições (texto == texto_original_gerado)
        - Rating 3: Laudo editado parcialmente (pequenas mudanças)
        - Rating 1: Laudo muito editado ou regenerado
        """
        texto_atual = laudo.get("texto", "")
        texto_original = laudo.get("texto_original_gerado", "")
        num_edicoes = laudo.get("num_edicoes", 0)
        
        if not texto_original:
            return None
        
        # Se não houve edições e textos são idênticos
        if num_edicoes == 0 and texto_atual.strip() == texto_original.strip():
            return 5
        
        # Calcular similaridade de texto (Levenshtein simplificado)
        similarity = self._calcular_similaridade_texto(texto_atual, texto_original)
        
        # Rating baseado em similaridade e número de edições
        if similarity >= 0.95 and num_edicoes <= 1:
            return 5  # Aprovado sem edições significativas
        elif similarity >= 0.70 and num_edicoes <= 3:
            return 3  # Editado parcialmente
        else:
            return 1  # Muito editado ou regenerado
    
    def _calcular_similaridade_texto(self, texto1: str, texto2: str) -> float:
        """Calcula similaridade entre dois textos (0.0 a 1.0)"""
        if not texto1 or not texto2:
            return 0.0
        
        # Normalizar textos
        t1 = texto1.strip().lower()
        t2 = texto2.strip().lower()
        
        if t1 == t2:
            return 1.0
        
        # Usar algoritmo simples de similaridade baseado em palavras comuns
        palavras1 = set(t1.split())
        palavras2 = set(t2.split())
        
        if not palavras1 or not palavras2:
            return 0.0
        
        palavras_comuns = palavras1.intersection(palavras2)
        palavras_total = palavras1.union(palavras2)
        
        if not palavras_total:
            return 0.0
        
        return len(palavras_comuns) / len(palavras_total)
    
    def registrar_edicao(self, laudo_id: str, novo_texto: str, admin_id: Optional[str] = None) -> bool:
        """Registra uma edição no laudo"""
        laudo = self.find_by_id(laudo_id)
        if not laudo:
            return False
        
        historico = laudo.get("historico_edicoes", [])
        historico.append({
            "texto_anterior": laudo.get("texto", ""),
            "texto_novo": novo_texto,
            "admin_id": admin_id,
            "timestamp": datetime.utcnow()
        })
        
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": {
                "texto": novo_texto,
                "num_edicoes": laudo.get("num_edicoes", 0) + 1,
                "historico_edicoes": historico,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0


class Fatura(BaseModel):
    """Modelo de fatura"""

    def create(self, user_id: str, periodo: str, exames: List[Dict],
               valor_total: float, status: str = "pendente") -> str:
        """Cria uma nova fatura"""
        fatura_data = {
            "user_id": user_id,
            "periodo": periodo,  # "YYYY-MM" ou "YYYY-MM-DD a YYYY-MM-DD"
            "exames": exames,  # Lista de dicts com {requisicao_id, valor, data}
            "valor_total": valor_total,
            "status": status,  # "pendente", "paga", "cancelada"
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "paga_at": None
        }
        result = self.collection.insert_one(fatura_data)
        return str(result.inserted_id)

    def find_by_id(self, fatura_id: str) -> Optional[Dict]:
        """Busca fatura por ID"""
        doc = self.collection.find_one({"_id": ObjectId(fatura_id)})
        return self.to_dict(doc) if doc else None

    def find_by_user(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Busca faturas de um usuário"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        docs = self.collection.find(query).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def find_all(self, periodo: Optional[str] = None,
                 status: Optional[str] = None) -> List[Dict]:
        """Lista todas as faturas"""
        query = {}
        if periodo:
            query["periodo"] = periodo
        if status:
            query["status"] = status
        docs = self.collection.find(query).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def update_status(self, fatura_id: str, status: str) -> bool:
        """Atualiza o status de uma fatura"""
        updates = {"status": status, "updated_at": datetime.utcnow()}
        if status == "paga":
            updates["paga_at"] = datetime.utcnow()

        result = self.collection.update_one(
            {"_id": ObjectId(fatura_id)},
            {"$set": updates}
        )
        return result.modified_count > 0


class KnowledgeBase(BaseModel):
    """Modelo de knowledge base"""

    def create(self, titulo: str, tipo: str, conteudo: str,
               tags: List[str] = None, arquivo_path: Optional[str] = None) -> str:
        """Cria um novo item na knowledge base"""
        kb_data = {
            "titulo": titulo,
            "tipo": tipo,  # "pdf", "prompt", "orientacao"
            "conteudo": conteudo,
            "tags": tags or [],
            "arquivo_path": arquivo_path,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(kb_data)
        return str(result.inserted_id)

    def find_by_id(self, kb_id: str) -> Optional[Dict]:
        """Busca item por ID"""
        doc = self.collection.find_one({"_id": ObjectId(kb_id)})
        return self.to_dict(doc) if doc else None

    def find_by_type(self, tipo: str) -> List[Dict]:
        """Busca itens por tipo"""
        docs = self.collection.find({"tipo": tipo}).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def find_by_tags(self, tags: List[str]) -> List[Dict]:
        """Busca itens por tags"""
        docs = self.collection.find({"tags": {"$in": tags}}).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def get_all(self) -> List[Dict]:
        """Lista todos os itens"""
        docs = self.collection.find().sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]


class LearningHistory(BaseModel):
    """Modelo para histórico de aprendizado do sistema"""

    def create(self, laudo_id: str, requisicao_id: str, 
               contexto: Dict, texto_gerado: str, texto_final: str,
               rating: int, modelo_usado: str, usado_api_externa: bool,
               similaridade_casos: Optional[float] = None,
               casos_similares: Optional[List[str]] = None) -> str:
        """Cria um registro de aprendizado"""
        history_data = {
            "laudo_id": laudo_id,
            "requisicao_id": requisicao_id,
            "contexto": contexto,  # Informações do paciente (especie, raca, etc.)
            "texto_gerado": texto_gerado,  # Texto original da IA
            "texto_final": texto_final,  # Texto final aprovado
            "rating": rating,  # 1, 3 ou 5
            "modelo_usado": modelo_usado,  # "local", "api_externa", "híbrido"
            "usado_api_externa": usado_api_externa,
            "similaridade_casos": similaridade_casos,
            "casos_similares": casos_similares or [],  # IDs de casos similares usados
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(history_data)
        return str(result.inserted_id)

    def find_by_laudo(self, laudo_id: str) -> Optional[Dict]:
        """Busca histórico por laudo"""
        doc = self.collection.find_one({"laudo_id": laudo_id})
        return self.to_dict(doc) if doc else None

    def find_similar_context(self, contexto: Dict, min_rating: int = 3, limit: int = 10) -> List[Dict]:
        """
        Busca casos similares baseado no contexto (especie, raca, região, suspeita)
        Retorna casos com rating >= min_rating
        """
        query = {
            "rating": {"$gte": min_rating}
        }
        
        # Filtrar por contexto similar
        if contexto.get("especie"):
            query["contexto.especie"] = contexto["especie"]
        if contexto.get("raca"):
            query["contexto.raca"] = contexto["raca"]
        if contexto.get("regiao_estudo"):
            query["contexto.regiao_estudo"] = contexto["regiao_estudo"]
        if contexto.get("suspeita_clinica"):
            # Busca parcial na suspeita clínica
            query["contexto.suspeita_clinica"] = {"$regex": contexto["suspeita_clinica"], "$options": "i"}
        
        docs = self.collection.find(query).sort([("rating", -1), ("created_at", -1)]).limit(limit)
        return [self.to_dict(doc) for doc in docs]

    def get_statistics(self) -> Dict:
        """Retorna estatísticas do sistema de aprendizado"""
        total = self.collection.count_documents({})
        rating_5 = self.collection.count_documents({"rating": 5})
        rating_3 = self.collection.count_documents({"rating": 3})
        rating_1 = self.collection.count_documents({"rating": 1})
        local_only = self.collection.count_documents({"usado_api_externa": False})
        api_used = self.collection.count_documents({"usado_api_externa": True})
        
        return {
            "total_casos": total,
            "rating_5": rating_5,
            "rating_3": rating_3,
            "rating_1": rating_1,
            "local_only": local_only,
            "api_used": api_used,
            "taxa_aprovacao": (rating_5 / total * 100) if total > 0 else 0,
            "economia_api": (local_only / total * 100) if total > 0 else 0
        }
