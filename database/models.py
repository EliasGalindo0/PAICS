"""
Modelos de dados para MongoDB
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from bson import ObjectId
from pymongo.collection import Collection
from utils.timezone import now


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
               primeiro_acesso: bool = True, senha_temporaria: str = None,
               clinica_id: Optional[str] = None) -> str:
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
            "clinica_id": clinica_id,
            "created_at": now(),
            "updated_at": now()
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
        updates["updated_at"] = now()
        result = self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete(self, user_id: str) -> bool:
        """Exclui um usuário"""
        result = self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0


class Clinica(BaseModel):
    """Modelo de clínica veterinária"""

    def create(self, nome: str, cnpj: str = "", endereco: str = "",
               numero: str = "", bairro: str = "", cidade: str = "", cep: str = "",
               telefone: str = "", email: str = "", ativa: bool = True) -> str:
        """Cria uma nova clínica"""
        data = {
            "nome": nome,
            "cnpj": cnpj,
            "endereco": endereco,
            "numero": numero,
            "bairro": bairro,
            "cidade": cidade,
            "cep": cep,
            "telefone": telefone,
            "email": email,
            "ativa": ativa,
            "criado_em": now(),
        }
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def find_by_id(self, clinica_id: str) -> Optional[Dict]:
        """Busca clínica por ID"""
        doc = self.collection.find_one({"_id": ObjectId(clinica_id)})
        return self.to_dict(doc) if doc else None

    def get_all(self, apenas_ativas: bool = True) -> List[Dict]:
        """Lista todas as clínicas"""
        query = {"ativa": True} if apenas_ativas else {}
        docs = self.collection.find(query).sort("nome", 1)
        return [self.to_dict(doc) for doc in docs]

    def update(self, clinica_id: str, updates: Dict) -> bool:
        """Atualiza uma clínica"""
        result = self.collection.update_one(
            {"_id": ObjectId(clinica_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete(self, clinica_id: str) -> bool:
        """Exclui uma clínica, desvinculando usuários e requisições, e removendo veterinários."""
        from database.connection import get_db
        db = get_db()
        db.users.update_many({"clinica_id": clinica_id}, {"$set": {"clinica_id": None}})
        db.veterinarios.delete_many({"clinica_id": clinica_id})
        db.requisicoes.update_many({"clinica_id": clinica_id}, {"$set": {"clinica_id": None}})
        result = self.collection.delete_one({"_id": ObjectId(clinica_id)})
        return result.deleted_count > 0


class Veterinario(BaseModel):
    """Modelo de médico veterinário (vinculado a uma clínica)"""

    def create(self, nome: str, crmv: str, clinica_id: str,
               email: str = "", ativo: bool = True) -> str:
        """Cria um novo veterinário"""
        data = {
            "nome": nome,
            "crmv": crmv,
            "clinica_id": clinica_id,
            "email": email,
            "ativo": ativo,
            "criado_em": now(),
        }
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def find_by_id(self, vet_id: str) -> Optional[Dict]:
        """Busca veterinário por ID"""
        doc = self.collection.find_one({"_id": ObjectId(vet_id)})
        return self.to_dict(doc) if doc else None

    def find_by_clinica(self, clinica_id: str, apenas_ativos: bool = True) -> List[Dict]:
        """Lista veterinários de uma clínica"""
        query = {"clinica_id": clinica_id}
        if apenas_ativos:
            query["ativo"] = True
        docs = self.collection.find(query).sort("nome", 1)
        return [self.to_dict(doc) for doc in docs]

    def update(self, vet_id: str, updates: Dict) -> bool:
        """Atualiza um veterinário"""
        result = self.collection.update_one(
            {"_id": ObjectId(vet_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete(self, vet_id: str) -> bool:
        """Remove um veterinário (soft: desativa)"""
        return self.update(vet_id, {"ativo": False})


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
            "created_at": now(),
            "last_used_at": now(),
            "expires_at": now() + timedelta(days=30),
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
            {"$set": {"last_used_at": now()}}
        )
        return result.modified_count > 0

    def deactivate(self, session_id: str) -> bool:
        """Desativa uma sessão específica"""
        result = self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"active": False, "deactivated_at": now()}}
        )
        return result.modified_count > 0

    def deactivate_all_user_sessions(self, user_id: str) -> int:
        """Desativa todas as sessões de um usuário (logout de todos os dispositivos)"""
        result = self.collection.update_many(
            {"user_id": user_id, "active": True},
            {"$set": {"active": False, "deactivated_at": now()}}
        )
        return result.modified_count

    def cleanup_expired(self) -> int:
        """Remove sessões expiradas"""
        result = self.collection.delete_many({
            "expires_at": {"$lt": now()}
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
               data_exame: Optional[datetime] = None, status: str = "pendente",
               clinica_id: Optional[str] = None, veterinario_id: Optional[str] = None) -> str:
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
            "data_exame": data_exame or now(),
            "status": status,
            "clinica_id": clinica_id,
            "veterinario_id": veterinario_id,
            "created_at": now(),
            "updated_at": now()
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
            {"$set": {"status": status, "updated_at": now()}}
        )
        return result.modified_count > 0

    def update(self, req_id: str, updates: Dict) -> bool:
        """Atualiza uma requisição (ex.: rascunho). Para edição pelo admin com histórico, use update_with_history."""
        updates["updated_at"] = now()
        result = self.collection.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": updates}
        )
        return result.modified_count > 0

    def add_observacao_usuario(self, req_id: str, texto: str, user_id: str) -> bool:
        """Adiciona uma observação enviada pelo usuário (sem editar a requisição). Mantém histórico."""
        if not texto or not texto.strip():
            return False
        entry = {
            "texto": texto.strip(),
            "created_at": now(),
            "user_id": user_id,
        }
        result = self.collection.update_one(
            {"_id": ObjectId(req_id)},
            {
                "$push": {"observacoes_usuario": entry},
                "$set": {"updated_at": now()},
            },
        )
        return result.modified_count > 0

    def update_with_history(
        self, req_id: str, updates: Dict, admin_id: str
    ) -> bool:
        """Atualiza a requisição e registra no histórico de edições (para auditoria)."""
        doc = self.collection.find_one({"_id": ObjectId(req_id)})
        if not doc:
            try:
                from utils.observability import log_db_error
                log_db_error("requisicao.update_with_history", Exception("documento não encontrado"), req_id)
            except Exception:
                pass
            return False
        doc = self.to_dict(doc)
        alteracoes = {}
        for key, novo_val in updates.items():
            if key in ("updated_at",):
                continue
            antigo = doc.get(key)
            if antigo != novo_val:
                alteracoes[key] = {"de": antigo, "para": novo_val}
        if not alteracoes:
            return False
        try:
            from utils.observability import log_state_update
            for k, v in alteracoes.items():
                log_state_update("requisicao", f"{k}:{req_id}", str(v.get("de", ""))[:80], str(v.get("para", ""))[:80])
        except Exception:
            pass
        updates["updated_at"] = now()
        historico_entry = {
            "alteracoes": alteracoes,
            "admin_id": admin_id,
            "created_at": now(),
        }
        result = self.collection.update_one(
            {"_id": ObjectId(req_id)},
            {
                "$set": updates,
                "$push": {"historico_edicoes": historico_entry},
            },
        )
        return result.modified_count > 0


class Laudo(BaseModel):
    """Modelo de laudo"""

    def create(self, requisicao_id: str, texto: str,
               texto_original: str = "", status: str = "pendente",
               admin_id: Optional[str] = None,
               modelo_usado: Optional[str] = None,
               usado_api_externa: bool = False,
               similaridade_casos: Optional[float] = None,
               imagens_usadas: Optional[List[str]] = None) -> str:
        """Cria um novo laudo"""
        laudo_data = {
            "requisicao_id": requisicao_id,
            "texto": texto,
            "texto_original": texto_original,
            "status": status,  # "pendente", "validado", "liberado", "rejeitado"
            "admin_id": admin_id,
            "created_at": now(),
            "updated_at": now(),
            "validado_at": None,
            "liberado_at": None,
            # Campos para aprendizado
            "modelo_usado": modelo_usado,  # "local", "api_externa", "híbrido"
            "usado_api_externa": usado_api_externa,
            "similaridade_casos": similaridade_casos,
            "rating": None,  # Será calculado quando liberado/editado
            "num_edicoes": 0,
            "texto_original_gerado": texto_original or texto,  # Versão original da IA
            "historico_edicoes": [],  # Lista de edições com timestamps
            "imagens_usadas": imagens_usadas or [],  # Caminhos das imagens enviadas à LLM
            "regenerado_com_correcoes": False,  # True se foi regenerado com correções do admin
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
        if "texto" in updates:
            try:
                from utils.observability import log_state_update
                doc = self.collection.find_one({"_id": ObjectId(laudo_id)})
                old_texto = (doc.get("texto") or "")[:200] if doc else ""
                new_texto = (updates.get("texto") or "")[:200]
                log_state_update("laudo", f"texto:{laudo_id}", old_texto, new_texto)
            except Exception:
                pass
        updates["updated_at"] = now()
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": updates}
        )
        if result.matched_count == 0 and "texto" in updates:
            try:
                from utils.observability import log_db_error
                log_db_error("laudo.update", Exception("documento não encontrado"), laudo_id)
            except Exception:
                pass
        return result.modified_count > 0

    def validate(self, laudo_id: str, admin_id: str) -> bool:
        """Valida um laudo"""
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": {
                "status": "validado",
                "admin_id": admin_id,
                "validado_at": now(),
                "updated_at": now()
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
            "liberado_at": now(),
            "updated_at": now()
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
        Calcula rating automático baseado em edições e correções:
        - Rating 5: Aprovado sem edição (referência gold)
        - Rating 4: Pequenas edições de formatação
        - Rating 3: Editado manualmente sem sistema de correções
        - Rating 2: Corrigido com regeneração e aprovado
        - Rating 1: Múltiplas tentativas ou reescrito
        """
        # Se foi regenerado com correções do especialista → rating 2
        if laudo.get("regenerado_com_correcoes"):
            return 2

        texto_atual = laudo.get("texto", "")
        texto_original = laudo.get("texto_original_gerado", "")
        num_edicoes = laudo.get("num_edicoes", 0)

        if not texto_original:
            return None

        # Se não houve edições e textos são idênticos
        if num_edicoes == 0 and texto_atual.strip() == texto_original.strip():
            return 5

        # Calcular similaridade de texto
        similarity = self._calcular_similaridade_texto(texto_atual, texto_original)

        # Rating baseado em similaridade e número de edições
        if similarity >= 0.95 and num_edicoes <= 1:
            return 5  # Aprovado sem edições significativas
        elif similarity >= 0.90 and num_edicoes <= 2:
            return 4  # Pequenas edições de formatação
        elif similarity >= 0.70 and num_edicoes <= 3:
            return 3  # Editado manualmente
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
            "timestamp": now()
        })

        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": {
                "texto": novo_texto,
                "num_edicoes": laudo.get("num_edicoes", 0) + 1,
                "historico_edicoes": historico,
                "updated_at": now()
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
            # Lista de dicts com breakdown por exame:
            # {
            #   requisicao_id, valor_base, plantao (bool),
            #   acrescimo_plantao, valor, data, observacao
            # }
            "exames": exames,
            "valor_total": valor_total,
            "status": status,  # "pendente", "paga", "cancelada"
            "created_at": now(),
            "updated_at": now(),
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
        updates = {"status": status, "updated_at": now()}
        if status == "paga":
            updates["paga_at"] = now()

        result = self.collection.update_one(
            {"_id": ObjectId(fatura_id)},
            {"$set": updates}
        )
        return result.modified_count > 0


class SystemConfig(BaseModel):
    """Configurações do sistema (ex.: financeiro, temas, etc.).

    Cada documento é armazenado com uma chave única (key) e pode manter
    histórico de alterações em um array "history".
    """

    def get_config(self, key: str) -> Optional[Dict]:
        doc = self.collection.find_one({"key": key})
        return self.to_dict(doc) if doc else None

    def get_value(self, key: str, default=None):
        cfg = self.get_config(key)
        if not cfg:
            return default
        return cfg.get("value", default)

    def set_value(self, key: str, value, changed_by: Optional[str] = None) -> bool:
        """Define um valor de configuração e registra histórico de alterações."""
        doc = self.collection.find_one({"key": key})
        history_entry = {
            "value": value,
            "changed_at": now(),
        }
        if changed_by:
            history_entry["changed_by"] = changed_by

        if doc:
            history = doc.get("history", [])
            history.append(history_entry)
            result = self.collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"value": value, "updated_at": now(), "history": history}}
            )
            return result.modified_count > 0

        # Novo documento de configuração
        cfg_data = {
            "key": key,
            "value": value,
            "created_at": now(),
            "updated_at": now(),
            "history": [history_entry],
        }
        self.collection.insert_one(cfg_data)
        return True


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
            "created_at": now(),
            "updated_at": now()
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
            "created_at": now(),
            "updated_at": now()
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
            query["contexto.suspeita_clinica"] = {
                "$regex": contexto["suspeita_clinica"], "$options": "i"}

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


class CorrecaoLaudo(BaseModel):
    """Modelo para correções de laudo (sistema de aprendizado com correções do especialista)"""

    def create(
        self,
        requisicao_id: str,
        laudo_id: str,
        texto_correcao: str,
        categoria: str,
        contexto: Dict,
        laudo_original: str,
        laudo_corrigido: str,
        rating: int,
        aprovado: bool = True,
    ) -> str:
        """Registra uma correção feita pelo admin (para aprendizado)"""
        data = {
            "requisicao_id": requisicao_id,
            "laudo_id": laudo_id,
            "texto_correcao": texto_correcao,
            "categoria": categoria,
            "contexto": contexto,
            "laudo_original": laudo_original,
            "laudo_corrigido": laudo_corrigido,
            "rating": rating,
            "aprovado": aprovado,
            "created_at": now(),
            "updated_at": now(),
        }
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def find_by_laudo(self, laudo_id: str) -> List[Dict]:
        """Busca correções associadas a um laudo"""
        docs = self.collection.find({"laudo_id": laudo_id}).sort("created_at", -1)
        return [self.to_dict(doc) for doc in docs]

    def find_by_contexto(self, contexto: Dict, limit: int = 10) -> List[Dict]:
        """
        Busca correções em casos similares (mesma espécie/raça/região) para injetar alertas no prompt.
        contexto: dict com especie, raca, regiao_estudo (ou regiao).
        """
        query = {}
        if contexto.get("especie"):
            query["contexto.especie"] = contexto["especie"]
        if contexto.get("raca"):
            query["contexto.raca"] = contexto["raca"]
        regiao = contexto.get("regiao_estudo") or contexto.get("regiao")
        if regiao:
            query["contexto.regiao_estudo"] = regiao
        if not query:
            return []
        docs = self.collection.find(query).sort("created_at", -1).limit(limit)
        return [self.to_dict(doc) for doc in docs]
