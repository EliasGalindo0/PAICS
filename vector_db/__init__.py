"""
Banco de dados vetorial (ChromaDB) para laudos e knowledge base
"""
from .vector_store import VectorStore, get_vector_store

__all__ = ["VectorStore", "get_vector_store"]
