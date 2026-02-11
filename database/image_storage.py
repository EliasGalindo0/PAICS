"""
Armazenamento de imagens no MongoDB (GridFS).
Persiste imagens entre deploys, sem depender de volume de arquivos.
Referências: ObjectId em string (24 hex). Retrocompatível com paths do filesystem.
"""
import os
import re
from typing import Optional, Tuple

from bson import ObjectId
from gridfs import GridFS

from database.connection import get_db

_BUCKET_NAME = "paics_images"


def _get_gridfs():
    """Retorna instância do GridFS para o bucket de imagens."""
    db = get_db()
    return GridFS(db, collection=_BUCKET_NAME)


def _is_valid_objectid(s: str) -> bool:
    """True se a string for um ObjectId válido (24 caracteres hexadecimais)."""
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r"^[a-fA-F0-9]{24}$", s.strip()))


def is_gridfs_ref(ref: str) -> bool:
    """True se a referência for um ID do GridFS (novo formato)."""
    return _is_valid_objectid(ref)


def save_image(data: bytes, filename: str, metadata: Optional[dict] = None) -> str:
    """
    Salva imagem no GridFS. Retorna o ID como string para guardar em requisicao.imagens.

    Args:
        data: Bytes da imagem
        filename: Nome original do arquivo (ex: imagem.jpg)
        metadata: Metadados opcionais (user_id, requisicao_id, etc.)
    """
    fs = _get_gridfs()
    meta = dict(metadata or {})
    meta["filename"] = filename
    file_id = fs.put(data, filename=filename, metadata=meta)
    return str(file_id)


def get_image(image_id: str) -> Optional[bytes]:
    """
    Recupera bytes da imagem pelo ID do GridFS.
    Retorna None se não encontrar ou ID inválido.
    """
    if not _is_valid_objectid(image_id):
        return None
    try:
        fs = _get_gridfs()
        grid_out = fs.get(ObjectId(image_id))
        return grid_out.read()
    except Exception:
        return None


def get_filename(ref: str) -> str:
    """Retorna o filename da imagem. Para GridFS lê só metadata; para path usa basename."""
    if is_gridfs_ref(ref):
        try:
            db = get_db()
            doc = db[f"{_BUCKET_NAME}.files"].find_one(
                {"_id": ObjectId(ref)}, {"filename": 1}
            )
            return (doc.get("filename") or "imagem") if doc else ref[:12]
        except Exception:
            return ref[:12]
    return os.path.basename(ref)


def get_image_bytes_and_filename(ref: str) -> Optional[Tuple[bytes, str]]:
    """
    Dado ref (GridFS id ou path de arquivo legacy), retorna (bytes, filename).
    Retrocompatível com paths no filesystem.
    """
    if is_gridfs_ref(ref):
        try:
            fs = _get_gridfs()
            grid_out = fs.get(ObjectId(ref))
            data = grid_out.read()
            filename = getattr(grid_out, "filename", "imagem") or "imagem"
            return (data, filename)
        except Exception:
            return None
    # Legacy: path no filesystem
    if os.path.isfile(ref):
        try:
            with open(ref, "rb") as f:
                return (f.read(), os.path.basename(ref))
        except Exception:
            return None
    abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ref.lstrip("/"))
    if os.path.isfile(abs_path):
        try:
            with open(abs_path, "rb") as f:
                return (f.read(), os.path.basename(ref))
        except Exception:
            return None
    return None
