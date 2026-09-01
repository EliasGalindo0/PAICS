"""
Gerenciador de Knowledge Base
"""
import os
# fitz (PyMuPDF) será importado lazy quando necessário (evita problemas de importação circular)
from typing import List, Dict, Optional
from database.connection import get_db
from database.models import KnowledgeBase


class KnowledgeBaseManager:
    """Gerenciador da knowledge base para armazenar PDFs, prompts e orientações"""

    def __init__(self, upload_dir: str = "knowledge_base_uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        self.db = get_db()
        self.kb_model = KnowledgeBase(self.db.knowledge_base)
        self._vector_store = None

    @property
    def vector_store(self):
        if self._vector_store is None:
            from vector_db.vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    def add_pdf(self, file_path: str, titulo: str, tags: List[str] = None,
                arquivo_nome: str = "") -> str:
        """
        Adiciona um PDF à knowledge base.
        Extrai texto, guarda um preview no Mongo e indexa trechos no Chroma
        (livros inteiros numa só embedding estouram RAM e o modelo).
        """
        from knowledge_base.pdf_text import (
            MIN_TEXT_CHARS,
            MONGO_PREVIEW_CHARS,
            chunk_text,
            extract_pdf_text,
        )

        try:
            texto_completo, n_pages = extract_pdf_text(file_path)
        except Exception as e:
            raise ValueError(f"Não foi possível ler o PDF: {e}") from e

        if len(texto_completo.strip()) < MIN_TEXT_CHARS:
            raise ValueError(
                "Este PDF quase não tem texto selecionável (provavelmente é escaneado). "
                "Use um PDF com texto real ou um OCR antes de enviar."
            )

        chunks = chunk_text(texto_completo)
        if not chunks:
            raise ValueError("Não foi possível indexar o conteúdo deste PDF.")

        preview = texto_completo[:MONGO_PREVIEW_CHARS]
        if len(texto_completo) > MONGO_PREVIEW_CHARS:
            preview += (
                f"\n\n[Preview: {len(preview)} de {len(texto_completo)} caracteres; "
                f"{n_pages} páginas; {len(chunks)} trechos indexados]"
            )

        kb_id = self.kb_model.create(
            titulo=titulo,
            tipo="pdf",
            conteudo=preview,
            tags=tags or [],
            arquivo_path=arquivo_nome or None,
        )

        tags_str = ",".join(tags or [])
        batch_size = 32
        try:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                self.vector_store.collection.add(
                    documents=batch,
                    ids=[f"kb_{kb_id}_{i + j}" for j in range(len(batch))],
                    metadatas=[
                        {
                            "kb_id": kb_id,
                            "tipo": "knowledge_base",
                            "titulo": titulo,
                            "tags": tags_str,
                            "chunk": i + j,
                        }
                        for j in range(len(batch))
                    ],
                )
        except Exception as e:
            try:
                self.delete(kb_id)
            except Exception:
                pass
            raise RuntimeError(f"Erro ao indexar PDF no banco vetorial: {e}") from e

        return kb_id

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
        """Busca na knowledge base usando busca vetorial (dedup por item)."""
        fetch = max(n_results * 4, n_results)
        results = self.vector_store.collection.query(
            query_texts=[query],
            n_results=fetch,
            where={"tipo": "knowledge_base"}
        )

        items = []
        seen = set()
        if results['ids'] and len(results['ids'][0]) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                kb_id = results['metadatas'][0][i].get('kb_id', '')
                if not kb_id or kb_id in seen:
                    continue
                kb_item = self.kb_model.find_by_id(kb_id)
                if not kb_item:
                    continue
                seen.add(kb_id)
                items.append({
                    'kb_item': kb_item,
                    'relevancia': 1 - results['distances'][0][i] if results['distances'] else 0,
                    'texto_match': results['documents'][0][i] if results['documents'] else ''
                })
                if len(items) >= n_results:
                    break

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
            self.vector_store.collection.delete(where={"kb_id": kb_id})
        except Exception:
            try:
                self.vector_store.collection.delete(ids=[f"kb_{kb_id}"])
            except Exception:
                pass
        from bson import ObjectId
        result = self.kb_model.collection.delete_one({"_id": ObjectId(kb_id)})
        return result.deleted_count > 0
