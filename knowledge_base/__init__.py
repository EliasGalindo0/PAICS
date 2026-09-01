"""
Módulo de Knowledge Base
"""

def __getattr__(name):
    if name == "KnowledgeBaseManager":
        from .kb_manager import KnowledgeBaseManager
        return KnowledgeBaseManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["KnowledgeBaseManager"]
