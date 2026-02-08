"""
VectorStore: armazenamento vetorial com ChromaDB para laudos e knowledge base
"""
import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings


class VectorStore:
    """Armazena e busca textos usando embeddings ChromaDB"""

    COLLECTION_LAUDOS = "paics_laudos"
    COLLECTION_KB = "paics_knowledge_base"

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_laudos: str = COLLECTION_LAUDOS,
        collection_kb: str = COLLECTION_KB,
    ):
        # ChromaDB persiste em disco; em Railway/Docker usar dir writable
        path = persist_directory or os.getenv("CHROMA_PERSIST_DIR", "vector_db/chroma_data")
        os.makedirs(path, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection_laudos = self._client.get_or_create_collection(
            name=collection_laudos,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection_kb = self._client.get_or_create_collection(
            name=collection_kb,
            metadata={"hnsw:space": "cosine"},
        )
        # Para kb_manager: expõe collection da KB (add, query)
        self.collection = self._collection_kb

    def add_laudo(
        self,
        laudo_id: str,
        texto: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Adiciona laudo validado ao store vetorial"""
        meta = metadata or {}
        # ChromaDB exige metadatas com valores primitivos (str, int, float)
        safe_meta = {
            k: str(v) if not isinstance(v, (int, float, bool)) else v
            for k, v in meta.items()
        }
        self._collection_laudos.add(
            documents=[texto],
            ids=[f"laudo_{laudo_id}"],
            metadatas=[{"laudo_id": laudo_id, **safe_meta}],
        )

    def search_similar(
        self,
        query_text: str,
        n_results: int = 5,
        collection: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Busca textos similares por embedding.
        Retorna lista de dicts com 'distancia', 'id', 'metadata', 'document'.
        """
        coll = self._collection_laudos if collection == "laudos" else self._collection_kb
        results = coll.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        items = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                dist = results["distances"][0][i] if results.get("distances") else 0.0
                items.append({
                    "id": doc_id,
                    "distancia": dist,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "document": results["documents"][0][i] if results.get("documents") else "",
                })
        return items
