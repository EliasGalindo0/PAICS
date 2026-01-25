"""
Modelos de dados para MongoDB
"""
from datetime import datetime
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
               admin_id: Optional[str] = None) -> str:
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
            "liberado_at": None
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

    def release(self, laudo_id: str) -> bool:
        """Libera um laudo para o usuário"""
        result = self.collection.update_one(
            {"_id": ObjectId(laudo_id)},
            {"$set": {
                "status": "liberado",
                "liberado_at": datetime.utcnow(),
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
