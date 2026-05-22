from datetime import datetime, timezone
import zoneinfo

# Fuso horário padrão da Rádio (São Paulo, UTC-3 / UTC-2 no horário de verão antigo)
TZ_LOCAL = zoneinfo.ZoneInfo("America/Sao_Paulo")

def now_local() -> datetime:
    """Retorna datetime atual com fuso horário local de São Paulo."""
    return datetime.now(tz=TZ_LOCAL)

def now_utc() -> datetime:
    """Retorna datetime atual com fuso horário UTC."""
    return datetime.now(tz=timezone.utc)

def to_local(dt: datetime) -> datetime:
    """Converte um datetime com timezone para o timezone local."""
    if dt.tzinfo is None:
        # Assume que é UTC se não tiver timezone definido
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_LOCAL)
