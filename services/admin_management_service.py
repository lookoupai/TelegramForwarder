from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from models.models import (
    Chat,
    ForwardRule,
    Keyword,
    MediaExtensions,
    MediaTypes,
    PushConfig,
    ReplaceRule,
    RSSConfig,
    RSSPattern,
    RuleSync,
)


class ChatOut(BaseModel):
    id: int
    telegram_chat_id: str
    name: Optional[str]


class RuleCreate(BaseModel):
    source_chat_id: Optional[int] = None
    target_chat_id: Optional[int] = None
    source_telegram_chat_id: Optional[str] = None
    target_telegram_chat_id: Optional[str] = None
    source_name: Optional[str] = Field(default=None, max_length=255)
    target_name: Optional[str] = Field(default=None, max_length=255)

    @validator("source_telegram_chat_id", "target_telegram_chat_id")
    def normalize_telegram_chat_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if trimmed.startswith("http") or trimmed.startswith("t.me") or "/" in trimmed or "@" in trimmed:
            raise ValueError("暂不支持 Telegram 链接/用户名，请填写数字 chat_id（可用 /bind 自动写入）")
        if not trimmed.lstrip("-").isdigit():
            raise ValueError("chat_id 必须为数字")
        return str(int(trimmed))

    @validator("target_chat_id", always=True)
    def validate_create_mode(cls, _value: Optional[int], values):
        source_chat_id = values.get("source_chat_id")
        target_chat_id = values.get("target_chat_id")
        source_tid = values.get("source_telegram_chat_id")
        target_tid = values.get("target_telegram_chat_id")

        by_pk = source_chat_id is not None or target_chat_id is not None
        by_tid = source_tid is not None or target_tid is not None

        if by_pk and by_tid:
            raise ValueError("请仅选择一种方式创建：chat_id(下拉) 或 telegram_chat_id(手动)")
        if by_pk:
            if source_chat_id is None or target_chat_id is None:
                raise ValueError("source_chat_id 与 target_chat_id 均为必填")
            if source_chat_id == target_chat_id:
                raise ValueError("source_chat_id 与 target_chat_id 不能相同")
            return target_chat_id
        if by_tid:
            if not source_tid or not target_tid:
                raise ValueError("source_telegram_chat_id 与 target_telegram_chat_id 均为必填")
            if source_tid == target_tid:
                raise ValueError("源/目标 chat_id 不能相同")
            return _value

        raise ValueError("请选择聊天或填写 chat_id")


class TemplateSettingsOut(BaseModel):
    userinfo_template: str
    time_template: str
    original_link_template: str


class TemplateSettingsUpdate(BaseModel):
    userinfo_template: Optional[str] = Field(default=None, max_length=1024)
    time_template: Optional[str] = Field(default=None, max_length=1024)
    original_link_template: Optional[str] = Field(default=None, max_length=1024)


class SyncRuleOut(BaseModel):
    id: int
    sync_rule_id: int
    source_chat_name: Optional[str]
    target_chat_name: Optional[str]


class SyncRuleCreate(BaseModel):
    sync_rule_id: int


class PushConfigOut(BaseModel):
    id: int
    enable_push_channel: bool
    push_channel: str
    media_send_mode: str


class PushSettingsOut(BaseModel):
    enable_push: bool
    enable_only_push: bool
    configs: List[PushConfigOut]


class PushSettingsUpdate(BaseModel):
    enable_push: Optional[bool]
    enable_only_push: Optional[bool]


class PushConfigCreate(BaseModel):
    enable_push_channel: bool = True
    push_channel: str = Field(..., min_length=1, max_length=2048)
    media_send_mode: str = Field(default="Single")

    @validator("media_send_mode")
    def validate_send_mode(cls, value: str) -> str:
        mode = (value or "").strip()
        if mode not in ("Single", "Multiple"):
            raise ValueError("media_send_mode 仅支持 Single / Multiple")
        return mode

    @validator("push_channel")
    def strip_channel(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("push_channel 不能为空")
        return trimmed


class PushConfigUpdate(BaseModel):
    enable_push_channel: Optional[bool]
    push_channel: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    media_send_mode: Optional[str]

    @validator("media_send_mode")
    def validate_send_mode(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        mode = (value or "").strip()
        if mode not in ("Single", "Multiple"):
            raise ValueError("media_send_mode 仅支持 Single / Multiple")
        return mode

    @validator("push_channel")
    def strip_channel(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("push_channel 不能为空")
        return trimmed


DEFAULT_USERINFO_TEMPLATE = "**{name}**"
DEFAULT_TIME_TEMPLATE = "{time}"
DEFAULT_ORIGINAL_LINK_TEMPLATE = "原始连接：{original_link}"
UFB_ITEM_OPTIONS = ("main", "content", "main_username", "content_username")


class UFBSettingsOut(BaseModel):
    is_ufb: bool
    ufb_domain: Optional[str]
    ufb_item: str


class UFBSettingsUpdate(BaseModel):
    is_ufb: Optional[bool]
    ufb_domain: Optional[str] = Field(default=None, max_length=512)
    ufb_item: Optional[str]

    @validator("ufb_item")
    def validate_item(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        item = value.strip()
        if item not in UFB_ITEM_OPTIONS:
            raise ValueError(f"ufb_item 仅支持: {', '.join(UFB_ITEM_OPTIONS)}")
        return item

    @validator("ufb_domain")
    def normalize_domain(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


def list_chats(session: Session) -> List[ChatOut]:
    chats = session.query(Chat).order_by(Chat.id.desc()).all()
    return [
        ChatOut(id=chat.id, telegram_chat_id=str(chat.telegram_chat_id), name=chat.name)
        for chat in chats
    ]


def create_rule(session: Session, payload: RuleCreate) -> ForwardRule:
    if payload.source_chat_id is not None and payload.target_chat_id is not None:
        source_chat = session.query(Chat).filter(Chat.id == payload.source_chat_id).first()
        target_chat = session.query(Chat).filter(Chat.id == payload.target_chat_id).first()
        if not source_chat:
            raise ValueError("源聊天不存在")
        if not target_chat:
            raise ValueError("目标聊天不存在")
    else:
        if not payload.source_telegram_chat_id or not payload.target_telegram_chat_id:
            raise ValueError("source_telegram_chat_id 与 target_telegram_chat_id 均为必填")
        source_chat = session.query(Chat).filter(Chat.telegram_chat_id == payload.source_telegram_chat_id).first()
        if not source_chat:
            source_chat = Chat(
                telegram_chat_id=payload.source_telegram_chat_id,
                name=(payload.source_name or None),
            )
            session.add(source_chat)
            session.flush()
        target_chat = session.query(Chat).filter(Chat.telegram_chat_id == payload.target_telegram_chat_id).first()
        if not target_chat:
            target_chat = Chat(
                telegram_chat_id=payload.target_telegram_chat_id,
                name=(payload.target_name or None),
            )
            session.add(target_chat)
            session.flush()

    rule = ForwardRule(source_chat_id=source_chat.id, target_chat_id=target_chat.id)
    session.add(rule)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("该源/目标组合的规则已存在")
    session.refresh(rule)
    return rule


def delete_rule(session: Session, rule_id: int) -> bool:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        return False

    session.query(Keyword).filter(Keyword.rule_id == rule_id).delete(synchronize_session=False)
    session.query(ReplaceRule).filter(ReplaceRule.rule_id == rule_id).delete(synchronize_session=False)
    session.query(RuleSync).filter(RuleSync.rule_id == rule_id).delete(synchronize_session=False)
    session.query(PushConfig).filter(PushConfig.rule_id == rule_id).delete(synchronize_session=False)
    session.query(MediaTypes).filter(MediaTypes.rule_id == rule_id).delete(synchronize_session=False)
    session.query(MediaExtensions).filter(MediaExtensions.rule_id == rule_id).delete(synchronize_session=False)

    rss_config = session.query(RSSConfig).filter(RSSConfig.rule_id == rule_id).first()
    if rss_config:
        session.query(RSSPattern).filter(RSSPattern.rss_config_id == rss_config.id).delete(synchronize_session=False)
        session.delete(rss_config)

    session.delete(rule)
    session.commit()
    return True


def get_template_settings(session: Session, rule_id: int) -> TemplateSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    return TemplateSettingsOut(
        userinfo_template=rule.userinfo_template or DEFAULT_USERINFO_TEMPLATE,
        time_template=rule.time_template or DEFAULT_TIME_TEMPLATE,
        original_link_template=rule.original_link_template or DEFAULT_ORIGINAL_LINK_TEMPLATE,
    )


def update_template_settings(session: Session, rule_id: int, payload: TemplateSettingsUpdate) -> TemplateSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")

    data = payload.dict(exclude_unset=True)
    if "userinfo_template" in data:
        value = (data["userinfo_template"] or "").strip()
        rule.userinfo_template = value or DEFAULT_USERINFO_TEMPLATE
    if "time_template" in data:
        value = (data["time_template"] or "").strip()
        rule.time_template = value or DEFAULT_TIME_TEMPLATE
    if "original_link_template" in data:
        value = (data["original_link_template"] or "").strip()
        rule.original_link_template = value or DEFAULT_ORIGINAL_LINK_TEMPLATE

    session.commit()
    return get_template_settings(session, rule_id)


def list_sync_rules(session: Session, rule_id: int) -> List[SyncRuleOut]:
    sync_rows = session.query(RuleSync).filter(RuleSync.rule_id == rule_id).order_by(RuleSync.id.desc()).all()
    if not sync_rows:
        return []

    target_ids = [row.sync_rule_id for row in sync_rows]
    targets = (
        session.query(ForwardRule)
        .options(joinedload(ForwardRule.source_chat), joinedload(ForwardRule.target_chat))
        .filter(ForwardRule.id.in_(target_ids))
        .all()
    )
    targets_map = {rule.id: rule for rule in targets}

    result: List[SyncRuleOut] = []
    for row in sync_rows:
        target = targets_map.get(row.sync_rule_id)
        result.append(
            SyncRuleOut(
                id=row.id,
                sync_rule_id=row.sync_rule_id,
                source_chat_name=getattr(getattr(target, "source_chat", None), "name", None),
                target_chat_name=getattr(getattr(target, "target_chat", None), "name", None),
            )
        )
    return result


def add_sync_rule(session: Session, rule_id: int, payload: SyncRuleCreate) -> List[SyncRuleOut]:
    if payload.sync_rule_id == rule_id:
        raise ValueError("不能同步到自身")
    exists = session.query(ForwardRule).filter(ForwardRule.id == payload.sync_rule_id).first()
    if not exists:
        raise ValueError("同步目标规则不存在")
    duplicate = (
        session.query(RuleSync)
        .filter(RuleSync.rule_id == rule_id, RuleSync.sync_rule_id == payload.sync_rule_id)
        .first()
    )
    if duplicate:
        return list_sync_rules(session, rule_id)

    row = RuleSync(rule_id=rule_id, sync_rule_id=payload.sync_rule_id)
    session.add(row)
    session.commit()
    return list_sync_rules(session, rule_id)


def delete_sync_rule(session: Session, rule_id: int, rule_sync_id: int) -> List[SyncRuleOut]:
    row = session.query(RuleSync).filter(RuleSync.rule_id == rule_id, RuleSync.id == rule_sync_id).first()
    if not row:
        return list_sync_rules(session, rule_id)
    session.delete(row)
    session.commit()
    return list_sync_rules(session, rule_id)


def get_push_settings(session: Session, rule_id: int) -> PushSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    rows = session.query(PushConfig).filter(PushConfig.rule_id == rule_id).order_by(PushConfig.id.desc()).all()
    return PushSettingsOut(
        enable_push=bool(rule.enable_push),
        enable_only_push=bool(rule.enable_only_push),
        configs=[
            PushConfigOut(
                id=row.id,
                enable_push_channel=bool(row.enable_push_channel),
                push_channel=row.push_channel,
                media_send_mode=row.media_send_mode,
            )
            for row in rows
        ],
    )


def get_ufb_settings(session: Session, rule_id: int) -> UFBSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    return UFBSettingsOut(
        is_ufb=bool(rule.is_ufb),
        ufb_domain=rule.ufb_domain,
        ufb_item=str(rule.ufb_item or "main"),
    )


def update_ufb_settings(session: Session, rule_id: int, payload: UFBSettingsUpdate) -> UFBSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)
    session.commit()
    return get_ufb_settings(session, rule_id)


def update_push_settings(session: Session, rule_id: int, payload: PushSettingsUpdate) -> PushSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)
    session.commit()
    return get_push_settings(session, rule_id)


def add_push_config(session: Session, rule_id: int, payload: PushConfigCreate) -> PushSettingsOut:
    exists = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not exists:
        raise ValueError("规则不存在")
    row = PushConfig(
        rule_id=rule_id,
        enable_push_channel=payload.enable_push_channel,
        push_channel=payload.push_channel,
        media_send_mode=payload.media_send_mode,
    )
    session.add(row)
    session.commit()
    return get_push_settings(session, rule_id)


def update_push_config(session: Session, push_config_id: int, payload: PushConfigUpdate) -> PushConfigOut:
    row = session.query(PushConfig).filter(PushConfig.id == push_config_id).first()
    if not row:
        raise ValueError("推送配置不存在")
    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(row, field, value)
    session.commit()
    session.refresh(row)
    return PushConfigOut(
        id=row.id,
        enable_push_channel=bool(row.enable_push_channel),
        push_channel=row.push_channel,
        media_send_mode=row.media_send_mode,
    )


def delete_push_config(session: Session, rule_id: int, push_config_id: int) -> PushSettingsOut:
    row = session.query(PushConfig).filter(PushConfig.id == push_config_id, PushConfig.rule_id == rule_id).first()
    if row:
        session.delete(row)
        session.commit()
    return get_push_settings(session, rule_id)
