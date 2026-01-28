"""
Utilitários de timezone para o sistema PAICS
Configurado para GMT-3 (Horário de Brasília)
"""
from datetime import datetime, timezone, timedelta

# Timezone GMT-3 (Horário de Brasília)
BRASILIA_TZ = timezone(timedelta(hours=-3))


def now() -> datetime:
    """
    Retorna o datetime atual no timezone GMT-3 (Horário de Brasília)
    Substitui datetime.utcnow() em todo o sistema
    """
    return datetime.now(BRASILIA_TZ)


def utc_to_local(utc_dt: datetime) -> datetime:
    """
    Converte um datetime UTC para o timezone local (GMT-3)
    Se não tiver timezone, assume que já está no timezone local
    """
    if utc_dt.tzinfo is None:
        # Se não tiver timezone, assumir que já está no timezone local
        # (para compatibilidade com dados antigos do MongoDB)
        return utc_dt.replace(tzinfo=BRASILIA_TZ)
    # Se tiver timezone UTC, converter para local
    if utc_dt.tzinfo == timezone.utc or (hasattr(utc_dt.tzinfo, 'utcoffset') and utc_dt.tzinfo.utcoffset(utc_dt) and utc_dt.tzinfo.utcoffset(utc_dt).total_seconds() == 0):
        return utc_dt.astimezone(BRASILIA_TZ)
    # Se já estiver em outro timezone, converter para local
    return utc_dt.astimezone(BRASILIA_TZ)


def local_to_utc(local_dt: datetime) -> datetime:
    """
    Converte um datetime local (GMT-3) para UTC
    """
    if local_dt.tzinfo is None:
        # Assumir que já está no timezone local
        local_dt = local_dt.replace(tzinfo=BRASILIA_TZ)
    return local_dt.astimezone(timezone.utc)


def get_date_start(dt: datetime) -> datetime:
    """
    Retorna o início do dia (00:00:00) no timezone local para uma data
    """
    local_dt = dt if dt.tzinfo else dt.replace(tzinfo=BRASILIA_TZ)
    return local_dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_date_end(dt: datetime) -> datetime:
    """
    Retorna o fim do dia (23:59:59.999999) no timezone local para uma data
    """
    local_dt = dt if dt.tzinfo else dt.replace(tzinfo=BRASILIA_TZ)
    return local_dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def combine_date_local(date_obj, time_obj=None) -> datetime:
    """
    Combina uma data com um horário no timezone local (GMT-3)
    Similar a datetime.combine mas com timezone
    """
    if time_obj is None:
        time_obj = datetime.min.time()
    dt = datetime.combine(date_obj, time_obj)
    return dt.replace(tzinfo=BRASILIA_TZ)
