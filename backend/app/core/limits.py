from app.db.models import Role

DAILY_ANALYSIS_LIMIT: dict[Role, int | None] = {
    Role.user: 10,
    Role.pro: None,
    Role.admin: None,
}


def get_daily_limit(role: Role) -> int | None:
    """None означает безлимит."""
    return DAILY_ANALYSIS_LIMIT[role]


def is_unlimited(role: Role) -> bool:
    return DAILY_ANALYSIS_LIMIT[role] is None
