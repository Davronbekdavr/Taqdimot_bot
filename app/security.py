def is_admin_id(telegram_id: int | None, admin_ids: frozenset[int]) -> bool:
    return telegram_id is not None and telegram_id in admin_ids


def is_super_admin_id(telegram_id: int | None, super_admin_ids: frozenset[int] | None = None) -> bool:
    """Authorize a super admin strictly by server-configured Telegram numeric ID."""
    if telegram_id is None:
        return False
    if super_admin_ids is None:
        from app.config import settings
        super_admin_ids = settings.super_admin_ids
    return telegram_id in super_admin_ids
