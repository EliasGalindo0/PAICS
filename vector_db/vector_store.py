"""
Banco de dados vetorial para aprendizado com laudos
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import hashlib


class VectorStore:
    """Gerenciador do banco de dados vetorial usando ChromaDB"""

    def __init__(self, persist_directory: str = "vector_db"):
        """Inicializa o banco de dados vetorial"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Inicializar ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Coleção para armazenar laudos
        self.collection = self.client.get_or_create_collection(
            name="laudos",
            metadata={"description": "Laudos veterinários para aprendizado"}
        )

    def add_laudo(self, laudo_id: str, texto: str, metadata: Dict = None) -> str:
        """
        Adiciona um laudo ao banco vetorial
        Retorna o ID do documento
        """
        # Criar ID único baseado no laudo_id
        doc_id = f"laudo_{laudo_id}"

        # Preparar metadados
        meta = metadata or {}
        meta['laudo_id'] = laudo_id
        meta['tipo'] = 'laudo'

        # Adicionar ao ChromaDB
        # ChromaDB automaticamente cria embeddings
        self.collection.add(
            documents=[texto],
            ids=[doc_id],
            metadatas=[meta]
        )

        return doc_id

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Busca laudos similares a uma query
        Retorna lista de dicts com {laudo_id, texto, distancia, metadata}
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )

        similar_laudos = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                similar_laudos.append({
                    'id': doc_id,
                    'texto': results['documents'][0][i] if results['documents'] else '',
                    'distancia': results['distances'][0][i] if results['distances'] else 0,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                })

        return similar_laudos

    def get_laudo(self, laudo_id: str) -> Optional[Dict]:
        """Busca um laudo específico pelo ID"""
        doc_id = f"laudo_{laudo_id}"
        results = self.collection.get(ids=[doc_id])

        if results['ids'] and len(results['ids']) > 0:
            idx = 0
            return {
                'id': results['ids'][idx],
                'texto': results['documents'][idx] if results['documents'] else '',
                'metadata': results['metadatas'][idx] if results['metadatas'] else {}
            }
        return None

    def delete_laudo(self, laudo_id: str) -> bool:
        """Remove um laudo do banco vetorial"""
        try:
            doc_id = f"laudo_{laudo_id}"
            self.collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def update_laudo(self, laudo_id: str, novo_texto: str, metadata: Dict = None) -> bool:
        """Atualiza um laudo existente"""
        try:
            doc_id = f"laudo_{laudo_id}"
            meta = metadata or {}
            meta['laudo_id'] = laudo_id
            meta['tipo'] = 'laudo'

            # ChromaDB não tem update direto, então deleta e recria
            self.collection.delete(ids=[doc_id])
            self.collection.add(
                documents=[novo_texto],
                ids=[doc_id],
                metadatas=[meta]
            )
            return True
        except Exception:
            return False

    def get_all_laudos(self) -> List[Dict]:
        """Retorna todos os laudos do banco vetorial"""
        results = self.collection.get()

        laudos = []
        if results['ids']:
            for i, doc_id in enumerate(results['ids']):
                laudos.append({
                    'id': results['ids'][i],
                    'texto': results['documents'][i] if results['documents'] else '',
                    'metadata': results['metadatas'][i] if results['metadatas'] else {}
                })

        return laudos

    def count(self) -> int:
        """Retorna o número de laudos no banco vetorial"""
        return self.collection.count()
