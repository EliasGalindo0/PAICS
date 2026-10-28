"""Erros do MongoDB Atlas (cota de armazenamento, ObjectId inválido)."""
from typing import Optional

from bson.errors import InvalidId

QUOTA_DETAIL = (
    "Armazenamento do MongoDB esgotado (512 MB). As escritas estão bloqueadas no Atlas. "
    "Exclua exames antigos com imagens ou faça upgrade do cluster. "
    "Isso não é causado pela chave da OpenAI."
)

_QUOTA_MARKERS = ("space quota", "writes are blocked", "over your space quota")


def is_storage_quota_error(exc: BaseException) -> bool:
    if getattr(exc, "code", None) == 8000:
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _QUOTA_MARKERS)


def is_invalid_id_error(exc: BaseException) -> bool:
    return isinstance(exc, InvalidId) or (
        isinstance(exc, Exception) and "not a valid ObjectId" in str(exc)
    )


def raise_if_storage_quota(exc: BaseException) -> None:
    """Re-lança HTTP 507 se o erro for cota do Atlas; caso contrário não faz nada."""
    if is_storage_quota_error(exc):
        from fastapi import HTTPException

        raise HTTPException(status_code=507, detail=QUOTA_DETAIL)


def json_status_for_unhandled(exc: Exception) -> Optional[tuple[int, str]]:
    """Retorna (status, detail) para o handler global, ou None para 500 genérico."""
    if is_invalid_id_error(exc):
        return 400, "Identificador inválido"
    if is_storage_quota_error(exc):
        return 507, QUOTA_DETAIL
    return None
