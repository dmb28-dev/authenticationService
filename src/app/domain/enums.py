from enum import StrEnum


class SessionRevocationReason(StrEnum):
    LOGOUT = "logout"
    SOFT_DELETE = "soft_delete"
    REFRESH_REUSE = "refresh_reuse"
    EXPIRED = "expired"


class AccessRuleChangeType(StrEnum):
    CREATE = "create"
    UPDATE = "update"
