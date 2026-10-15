from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import AuditEvent

FORBIDDEN_LOG_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "api_key",
    "llm_api_key",
    "secret",
}


def sanitize_metadata(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not data:
        return {}
    cleaned: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in FORBIDDEN_LOG_KEYS:
            continue
        if isinstance(v, dict):
            cleaned[k] = sanitize_metadata(v)
        else:
            cleaned[k] = v
    return cleaned


def log_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    actor_id: Optional[int] = None,
    actor_role: Optional[str] = None,
    rule_version: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        rule_version=rule_version or settings.RULE_ENGINE_VERSION,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(event)
    db.flush()
    return event
