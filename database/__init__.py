"""
Módulo de banco de dados - MongoDB
"""
from .connection import get_db, init_db
from .models import User, Laudo, Requisicao, Fatura, KnowledgeBase, LearningHistory, CorrecaoLaudo

__all__ = ['get_db', 'init_db', 'User', 'Laudo', 'Requisicao', 'Fatura', 'KnowledgeBase', 'LearningHistory', 'CorrecaoLaudo']
