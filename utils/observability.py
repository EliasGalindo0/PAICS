"""
Observabilidade do PAICS — focado em erros para manutenção.
- Logue apenas falhas, respostas inesperadas e alterações de estado críticas.
- Evite logs de sucesso para reduzir ruído.
"""
import logging

# Logger principal para erros do app
log = logging.getLogger("paics")

# Sub-loggers por domínio (todos propagam para paics)
log_api = logging.getLogger("paics.api")
log_db = logging.getLogger("paics.db")
log_state = logging.getLogger("paics.state")
log_auth = logging.getLogger("paics.auth")


def log_api_error(source: str, error: Exception, context: str = "") -> None:
    """Log de erro em chamada de API externa."""
    log_api.error(
        "API %s falhou | context=%s | error=%s",
        source,
        context or "(nenhum)",
        error,
        exc_info=True,
    )


def log_api_response_unexpected(source: str, response_preview: str, context: str = "") -> None:
    """Log quando API retorna algo inesperado (ex.: texto de erro)."""
    preview = (response_preview or "")[:200].replace("\n", " ")
    log_api.warning(
        "API %s retornou resposta inesperada | context=%s | preview=%s...",
        source,
        context or "(nenhum)",
        preview,
    )


def log_db_error(operation: str, error: Exception, identifier: str = "") -> None:
    """Log de erro em operação de banco."""
    log_db.error(
        "DB %s falhou | id=%s | error=%s",
        operation,
        identifier or "(nenhum)",
        error,
        exc_info=True,
    )


def log_state_update(component: str, key: str, from_val: str, to_val: str) -> None:
    """Log de atualização de estado que pode afetar UI (texto, formulários)."""
    # Truncar valores longos
    f = str(from_val)[:80] + "..." if len(str(from_val)) > 80 else str(from_val)
    t = str(to_val)[:80] + "..." if len(str(to_val)) > 80 else str(to_val)
    log_state.warning(
        "Estado alterado | component=%s key=%s | from=%s | to=%s",
        component,
        key,
        f,
        t,
    )
