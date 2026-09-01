"""Rotas de Knowledge Base (admin)"""
import os
import tempfile
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from api.dependencies import require_admin

router = APIRouter(prefix="/api", tags=["knowledge_base"])

_MAX_PDF_MB = 95
_MAX_PDF_BYTES = _MAX_PDF_MB * 1024 * 1024


def _kb_manager():
    from knowledge_base.kb_manager import KnowledgeBaseManager
    return KnowledgeBaseManager()


def _learning_system():
    from ai.learning_system import LearningSystem
    return LearningSystem()


class PromptCreate(BaseModel):
    titulo: str
    conteudo: str
    tags: Optional[List[str]] = None


class OrientacaoCreate(BaseModel):
    titulo: str
    conteudo: str
    tags: Optional[List[str]] = None


@router.get("/knowledge-base")
def listar_kb(tipo: Optional[str] = None, user: dict = Depends(require_admin)):
    """Lista itens da knowledge base."""
    kb_manager = _kb_manager()
    items = kb_manager.get_all(tipo=tipo)
    # Serializar ObjectId e datas
    return [
        {
            "id": str(it.get("id", "")),
            "titulo": it.get("titulo", ""),
            "tipo": it.get("tipo", ""),
            "tags": it.get("tags", []),
            "created_at": str(it.get("created_at", "")),
            "conteudo_preview": (it.get("conteudo", "") or "")[:300],
        }
        for it in items
    ]


@router.get("/knowledge-base/search")
def buscar_kb(q: str, n: int = 5, user: dict = Depends(require_admin)):
    """Busca na knowledge base por similaridade."""
    if not q.strip():
        return []
    kb_manager = _kb_manager()
    results = kb_manager.search(q.strip(), n_results=n)
    return [
        {
            "kb_item": {
                "id": str(r["kb_item"].get("id", "")),
                "titulo": r["kb_item"].get("titulo", ""),
                "tipo": r["kb_item"].get("tipo", ""),
                "tags": r["kb_item"].get("tags", []),
                "conteudo": r["kb_item"].get("conteudo", ""),
            },
            "relevancia": r.get("relevancia", 0),
            "texto_match": r.get("texto_match", "")[:500],
        }
        for r in results
    ]


@router.get("/knowledge-base/learning/stats")
def stats_aprendizado(user: dict = Depends(require_admin)):
    """Estatísticas do sistema de aprendizado contínuo."""
    try:
        ls = _learning_system()
        return ls.get_statistics()
    except Exception as e:
        return {
            "total_casos": 0,
            "rating_5": 0,
            "rating_3": 0,
            "rating_1": 0,
            "local_only": 0,
            "api_used": 0,
            "taxa_aprovacao": 0,
            "economia_api": 0,
            "erro": str(e),
        }


@router.get("/knowledge-base/{kb_id}")
def obter_kb(kb_id: str, user: dict = Depends(require_admin)):
    """Obtém um item da knowledge base."""
    kb_manager = _kb_manager()
    item = kb_manager.get_by_id(kb_id)
    if not item:
        raise HTTPException(404, "Item não encontrado")
    return {
        "id": str(item.get("id", "")),
        "titulo": item.get("titulo", ""),
        "tipo": item.get("tipo", ""),
        "tags": item.get("tags", []),
        "conteudo": item.get("conteudo", ""),
        "created_at": str(item.get("created_at", "")),
        "arquivo_path": item.get("arquivo_path"),
    }


@router.post("/knowledge-base/pdf")
async def adicionar_pdf(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    tags: str = Form(""),
    user: dict = Depends(require_admin),
):
    """Adiciona um PDF à knowledge base."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Arquivo deve ser PDF")
    if not titulo.strip():
        raise HTTPException(400, "Título é obrigatório")
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    tmp_path = None
    try:
        total = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_PDF_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"PDF maior que {_MAX_PDF_MB} MB. "
                            "Divida o livro em partes menores ou use um PDF com texto (não só imagens)."
                        ),
                    )
                tmp.write(chunk)
        if total == 0:
            raise HTTPException(400, "Arquivo vazio")
        kb_manager = _kb_manager()
        kb_id = kb_manager.add_pdf(
            tmp_path, titulo.strip(), tags_list, arquivo_nome=file.filename
        )
        return {"success": True, "id": kb_id, "mensagem": "PDF adicionado com sucesso"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar PDF: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/knowledge-base/prompt")
def adicionar_prompt(body: PromptCreate, user: dict = Depends(require_admin)):
    """Adiciona um prompt à knowledge base."""
    if not body.titulo.strip():
        raise HTTPException(400, "Título é obrigatório")
    if not body.conteudo.strip():
        raise HTTPException(400, "Conteúdo é obrigatório")
    kb_manager = _kb_manager()
    kb_id = kb_manager.add_prompt(body.titulo.strip(), body.conteudo.strip(), body.tags or [])
    return {"success": True, "id": kb_id, "mensagem": "Prompt adicionado com sucesso"}


@router.post("/knowledge-base/orientacao")
def adicionar_orientacao(body: OrientacaoCreate, user: dict = Depends(require_admin)):
    """Adiciona uma orientação à knowledge base."""
    if not body.titulo.strip():
        raise HTTPException(400, "Título é obrigatório")
    if not body.conteudo.strip():
        raise HTTPException(400, "Conteúdo é obrigatório")
    kb_manager = _kb_manager()
    kb_id = kb_manager.add_orientacao(body.titulo.strip(), body.conteudo.strip(), body.tags or [])
    return {"success": True, "id": kb_id, "mensagem": "Orientação adicionada com sucesso"}


@router.delete("/knowledge-base/{kb_id}")
def excluir_kb(kb_id: str, user: dict = Depends(require_admin)):
    """Exclui um item da knowledge base."""
    kb_manager = _kb_manager()
    if not kb_manager.delete(kb_id):
        raise HTTPException(404, "Item não encontrado")
    return {"success": True, "mensagem": "Item excluído"}
