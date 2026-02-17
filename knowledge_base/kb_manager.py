"""
Gerenciador de Knowledge Base
"""
import os
# fitz (PyMuPDF) será importado lazy quando necessário (evita problemas de importação circular)
from typing import List, Dict, Optional
from database.connection import get_db
from database.models import KnowledgeBase
from vector_db.vector_store import VectorStore


class KnowledgeBaseManager:
    """Gerenciador da knowledge base para armazenar PDFs, prompts e orientações"""

    def __init__(self, upload_dir: str = "knowledge_base_uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        self.db = get_db()
        self.kb_model = KnowledgeBase(self.db.knowledge_base)
        self.vector_store = VectorStore()

    def add_pdf(self, file_path: str, titulo: str, tags: List[str] = None) -> str:
        """
        Adiciona um PDF à knowledge base
        Extrai texto do PDF e armazena no banco vetorial
        """
        try:
            # Importação lazy para evitar problemas de importação circular
            import fitz  # PyMuPDF
            
            # Extrair texto do PDF
            doc = fitz.open(file_path)
            texto_completo = ""

            for page in doc:
                texto_completo += page.get_text()

            doc.close()

            # Salvar na knowledge base
            kb_id = self.kb_model.create(
                titulo=titulo,
                tipo="pdf",
                conteudo=texto_completo,
                tags=tags or [],
                arquivo_path=file_path
            )

            # Adicionar ao banco vetorial
            self.vector_store.collection.add(
                documents=[texto_completo],
                ids=[f"kb_{kb_id}"],
                metadatas=[{
                    "kb_id": kb_id,
                    "tipo": "knowledge_base",
                    "titulo": titulo,
                    "tags": ",".join(tags or [])
                }]
            )

            return kb_id

        except Exception as e:
            raise Exception(f"Erro ao adicionar PDF: {str(e)}")

    def add_prompt(self, titulo: str, conteudo: str, tags: List[str] = None) -> str:
        """Adiciona um prompt à knowledge base"""
        kb_id = self.kb_model.create(
            titulo=titulo,
            tipo="prompt",
            conteudo=conteudo,
            tags=tags or []
        )

        # Adicionar ao banco vetorial
        self.vector_store.collection.add(
            documents=[conteudo],
            ids=[f"kb_{kb_id}"],
            metadatas=[{
                "kb_id": kb_id,
                "tipo": "knowledge_base",
                "titulo": titulo,
                "tags": ",".join(tags or [])
            }]
        )

        return kb_id

    def add_orientacao(self, titulo: str, conteudo: str, tags: List[str] = None) -> str:
        """Adiciona uma orientação à knowledge base"""
        kb_id = self.kb_model.create(
            titulo=titulo,
            tipo="orientacao",
            conteudo=conteudo,
            tags=tags or []
        )

        # Adicionar ao banco vetorial
        self.vector_store.collection.add(
            documents=[conteudo],
            ids=[f"kb_{kb_id}"],
            metadatas=[{
                "kb_id": kb_id,
                "tipo": "knowledge_base",
                "titulo": titulo,
                "tags": ",".join(tags or [])
            }]
        )

        return kb_id

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Busca na knowledge base usando busca vetorial"""
        results = self.vector_store.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"tipo": "knowledge_base"}
        )

        items = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                kb_id = results['metadatas'][0][i].get('kb_id', '')
                kb_item = self.kb_model.find_by_id(kb_id)

                if kb_item:
                    items.append({
                        'kb_item': kb_item,
                        'relevancia': 1 - results['distances'][0][i] if results['distances'] else 0,
                        'texto_match': results['documents'][0][i] if results['documents'] else ''
                    })

        return items

    def get_all(self, tipo: Optional[str] = None) -> List[Dict]:
        """Lista todos os itens da knowledge base"""
        if tipo:
            return self.kb_model.find_by_type(tipo)
        return self.kb_model.get_all()

    def get_by_id(self, kb_id: str) -> Optional[Dict]:
        """Busca item por ID"""
        return self.kb_model.find_by_id(kb_id)

    def delete(self, kb_id: str) -> bool:
        """Remove item da knowledge base (MongoDB + ChromaDB)"""
        item = self.kb_model.find_by_id(kb_id)
        if not item:
            return False
        try:
            self.vector_store.collection.delete(ids=[f"kb_{kb_id}"])
        except Exception:
            pass  # Pode não existir no Chroma se foi criado antes
        from bson import ObjectId
        result = self.kb_model.collection.delete_one({"_id": ObjectId(kb_id)})
        return result.deleted_count > 0
