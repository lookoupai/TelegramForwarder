from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session, joinedload

from enums.enums import AddMode, ForwardMode, HandleMode, MessageMode, PreviewMode
from models.models import ForwardRule
from services.rule_settings import RULE_SETTINGS


ADMIN_SETTING_FIELDS = [
    "enable_rule",
    "forward_mode",
    "add_mode",
    "use_bot",
    "is_filter_user_info",
    "is_replace",
    "message_mode",
    "is_preview",
    "is_original_link",
    "is_delete_original",
    "is_original_sender",
    "is_original_time",
    "enable_delay",
    "delay_seconds",
    "handle_mode",
    "enable_comment_button",
    "only_rss",
    "enable_sync",
]


class RuleSummary(BaseModel):
    id: int
    source_chat_name: Optional[str]
    source_chat_id: Optional[str]
    target_chat_name: Optional[str]
    target_chat_id: Optional[str]
    enable_rule: bool
    forward_mode: ForwardMode
    add_mode: AddMode
    use_bot: bool
    handle_mode: HandleMode
    only_rss: bool
    enable_sync: bool
    enable_delay: bool
    delay_seconds: Optional[int]
    keywords_count: int = 0
    replace_count: int = 0

    class Config:
        use_enum_values = True


class RuleDetail(RuleSummary):
    is_filter_user_info: bool
    is_replace: bool
    message_mode: MessageMode
    is_preview: PreviewMode
    is_original_link: bool
    is_delete_original: bool
    is_original_sender: bool
    is_original_time: bool
    enable_comment_button: bool


class RuleUpdate(BaseModel):
    enable_rule: Optional[bool]
    forward_mode: Optional[ForwardMode]
    add_mode: Optional[AddMode]
    use_bot: Optional[bool]
    is_filter_user_info: Optional[bool]
    is_replace: Optional[bool]
    message_mode: Optional[MessageMode]
    is_preview: Optional[PreviewMode]
    is_original_link: Optional[bool]
    is_delete_original: Optional[bool]
    is_original_sender: Optional[bool]
    is_original_time: Optional[bool]
    enable_delay: Optional[bool]
    delay_seconds: Optional[int]
    handle_mode: Optional[HandleMode]
    enable_comment_button: Optional[bool]
    only_rss: Optional[bool]
    enable_sync: Optional[bool]

    @validator("delay_seconds")
    def validate_delay(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value <= 0:
            raise ValueError("delay_seconds 必须大于 0")
        return value


def list_rules(session: Session) -> List[RuleSummary]:
    rules = (
        session.query(ForwardRule)
        .options(
            joinedload(ForwardRule.source_chat),
            joinedload(ForwardRule.target_chat),
            joinedload(ForwardRule.keywords),
            joinedload(ForwardRule.replace_rules),
        )
        .order_by(ForwardRule.id.desc())
        .all()
    )
    return [RuleSummary(**_serialize_rule(rule)) for rule in rules]


def get_rule_detail(session: Session, rule_id: int) -> Optional[RuleDetail]:
    rule = (
        session.query(ForwardRule)
        .options(
            joinedload(ForwardRule.source_chat),
            joinedload(ForwardRule.target_chat),
            joinedload(ForwardRule.keywords),
            joinedload(ForwardRule.replace_rules),
        )
        .filter(ForwardRule.id == rule_id)
        .first()
    )
    if not rule:
        return None
    return RuleDetail(**_serialize_rule(rule))


def update_rule_settings(session: Session, rule_id: int, payload: RuleUpdate) -> Optional[RuleDetail]:
    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        return get_rule_detail(session, rule_id)

    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        return None

    for field, value in update_data.items():
        if field not in ADMIN_SETTING_FIELDS:
            continue
        setattr(rule, field, value)

    session.commit()
    session.refresh(rule)
    return get_rule_detail(session, rule_id)


def get_setting_schema() -> Dict[str, Dict[str, Any]]:
    schema: Dict[str, Dict[str, Any]] = {}
    for field, config in RULE_SETTINGS.items():
        if field not in ADMIN_SETTING_FIELDS:
            continue

        field_info: Dict[str, Any] = {"label": config.get("display_name", field)}
        values = config.get("values")
        if values:
            field_info["options"] = [
                {
                    "value": _serialize_setting_value(option_value),
                    "label": option_label,
                }
                for option_value, option_label in values.items()
            ]
            field_info["type"] = "select"
        elif field == "delay_seconds":
            field_info["type"] = "number"
        else:
            field_info["type"] = "boolean"

        schema[field] = field_info
    return schema


def _serialize_rule(rule: ForwardRule) -> Dict[str, Any]:
    return {
        "id": rule.id,
        "source_chat_name": getattr(rule.source_chat, "name", None),
        "source_chat_id": getattr(rule.source_chat, "telegram_chat_id", None),
        "target_chat_name": getattr(rule.target_chat, "name", None),
        "target_chat_id": getattr(rule.target_chat, "telegram_chat_id", None),
        "enable_rule": rule.enable_rule,
        "forward_mode": rule.forward_mode,
        "add_mode": rule.add_mode,
        "use_bot": rule.use_bot,
        "handle_mode": rule.handle_mode,
        "only_rss": rule.only_rss,
        "enable_sync": rule.enable_sync,
        "enable_delay": rule.enable_delay,
        "delay_seconds": rule.delay_seconds,
        "is_filter_user_info": rule.is_filter_user_info,
        "is_replace": rule.is_replace,
        "message_mode": rule.message_mode,
        "is_preview": rule.is_preview,
        "is_original_link": rule.is_original_link,
        "is_delete_original": rule.is_delete_original,
        "is_original_sender": rule.is_original_sender,
        "is_original_time": rule.is_original_time,
        "enable_comment_button": rule.enable_comment_button,
        "keywords_count": len(rule.keywords or []),
        "replace_count": len(rule.replace_rules or []),
    }


def _serialize_setting_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if value in (None, ""):
        return ""
    return value
