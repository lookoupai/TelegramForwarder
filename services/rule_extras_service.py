from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from enums.enums import AddMode
from models.models import ForwardRule, Keyword, MediaExtensions, MediaTypes, ReplaceRule
from utils.settings import load_ai_models


class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=512)
    is_regex: bool = False
    is_blacklist: bool = True

    @validator("keyword")
    def strip_keyword(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("keyword 不能为空")
        return trimmed


class KeywordOut(BaseModel):
    id: int
    keyword: Optional[str]
    is_regex: bool
    is_blacklist: bool


class ReplaceRuleCreate(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=1024)
    content: Optional[str] = Field(default=None, max_length=4096)

    @validator("pattern")
    def strip_pattern(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("pattern 不能为空")
        return trimmed


class ReplaceRuleOut(BaseModel):
    id: int
    pattern: str
    content: Optional[str]


class MediaTypesOut(BaseModel):
    photo: bool
    document: bool
    video: bool
    audio: bool
    voice: bool


class MediaTypesUpdate(BaseModel):
    photo: Optional[bool]
    document: Optional[bool]
    video: Optional[bool]
    audio: Optional[bool]
    voice: Optional[bool]


class MediaExtensionOut(BaseModel):
    id: int
    extension: str


class MediaSettingsOut(BaseModel):
    enable_media_type_filter: bool
    enable_media_size_filter: bool
    max_media_size: int
    is_send_over_media_size_message: bool
    enable_extension_filter: bool
    extension_filter_mode: AddMode
    media_allow_text: bool
    media_types: MediaTypesOut
    extensions: List[MediaExtensionOut]

    class Config:
        use_enum_values = True


class MediaSettingsUpdate(BaseModel):
    enable_media_type_filter: Optional[bool]
    enable_media_size_filter: Optional[bool]
    max_media_size: Optional[int] = Field(default=None, ge=1, le=2048)
    is_send_over_media_size_message: Optional[bool]
    enable_extension_filter: Optional[bool]
    extension_filter_mode: Optional[AddMode]
    media_allow_text: Optional[bool]
    media_types: Optional[MediaTypesUpdate]


class MediaExtensionCreate(BaseModel):
    extension: str = Field(..., min_length=1, max_length=64)

    @validator("extension")
    def normalize_extension(cls, value: str) -> str:
        trimmed = value.strip().lower()
        if trimmed.startswith("."):
            trimmed = trimmed[1:]
        if not trimmed:
            raise ValueError("extension 不能为空")
        return trimmed


class AISettingsOut(BaseModel):
    is_ai: bool
    ai_model: Optional[str]
    ai_prompt: Optional[str]
    enable_ai_upload_image: bool
    is_keyword_after_ai: bool
    is_summary: bool
    summary_time: str
    summary_prompt: Optional[str]
    is_top_summary: bool
    available_models: List[str]


class AISettingsUpdate(BaseModel):
    is_ai: Optional[bool]
    ai_model: Optional[str]
    ai_prompt: Optional[str]
    enable_ai_upload_image: Optional[bool]
    is_keyword_after_ai: Optional[bool]
    is_summary: Optional[bool]
    summary_time: Optional[str]
    summary_prompt: Optional[str]
    is_top_summary: Optional[bool]

    @validator("ai_model")
    def normalize_ai_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @validator("summary_time")
    def validate_summary_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not re.match(r"^\d{2}:\d{2}$", trimmed):
            raise ValueError("summary_time 格式必须为 HH:MM")
        hour, minute = map(int, trimmed.split(":"))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("summary_time 超出范围")
        return trimmed


def list_keywords(session: Session, rule_id: int) -> List[KeywordOut]:
    keywords = (
        session.query(Keyword)
        .filter(Keyword.rule_id == rule_id)
        .order_by(Keyword.id.desc())
        .all()
    )
    return [KeywordOut(id=row.id, keyword=row.keyword, is_regex=row.is_regex, is_blacklist=row.is_blacklist) for row in keywords]


def create_keyword(session: Session, rule_id: int, payload: KeywordCreate) -> KeywordOut:
    row = Keyword(
        rule_id=rule_id,
        keyword=payload.keyword,
        is_regex=payload.is_regex,
        is_blacklist=payload.is_blacklist,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("关键字已存在（同规则/同类型）")
    session.refresh(row)
    return KeywordOut(id=row.id, keyword=row.keyword, is_regex=row.is_regex, is_blacklist=row.is_blacklist)


def delete_keyword(session: Session, keyword_id: int) -> bool:
    row = session.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not row:
        return False
    session.delete(row)
    session.commit()
    return True


def list_replace_rules(session: Session, rule_id: int) -> List[ReplaceRuleOut]:
    rows = (
        session.query(ReplaceRule)
        .filter(ReplaceRule.rule_id == rule_id)
        .order_by(ReplaceRule.id.desc())
        .all()
    )
    return [ReplaceRuleOut(id=row.id, pattern=row.pattern, content=row.content) for row in rows]


def create_replace_rule(session: Session, rule_id: int, payload: ReplaceRuleCreate) -> ReplaceRuleOut:
    row = ReplaceRule(rule_id=rule_id, pattern=payload.pattern, content=payload.content)
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("替换规则已存在（同规则/同 pattern/content）")
    session.refresh(row)
    return ReplaceRuleOut(id=row.id, pattern=row.pattern, content=row.content)


def delete_replace_rule(session: Session, replace_rule_id: int) -> bool:
    row = session.query(ReplaceRule).filter(ReplaceRule.id == replace_rule_id).first()
    if not row:
        return False
    session.delete(row)
    session.commit()
    return True


def _get_or_create_media_types(session: Session, rule_id: int) -> MediaTypes:
    row = session.query(MediaTypes).filter(MediaTypes.rule_id == rule_id).first()
    if row:
        return row
    row = MediaTypes(rule_id=rule_id)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_media_settings(session: Session, rule_id: int) -> MediaSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")

    media_types = _get_or_create_media_types(session, rule_id)
    extensions = (
        session.query(MediaExtensions)
        .filter(MediaExtensions.rule_id == rule_id)
        .order_by(MediaExtensions.id.desc())
        .all()
    )
    extension_values = [MediaExtensionOut(id=row.id, extension=row.extension) for row in extensions]

    return MediaSettingsOut(
        enable_media_type_filter=bool(rule.enable_media_type_filter),
        enable_media_size_filter=bool(rule.enable_media_size_filter),
        max_media_size=int(rule.max_media_size or 1),
        is_send_over_media_size_message=bool(rule.is_send_over_media_size_message),
        enable_extension_filter=bool(rule.enable_extension_filter),
        extension_filter_mode=rule.extension_filter_mode,
        media_allow_text=bool(rule.media_allow_text),
        media_types=MediaTypesOut(
            photo=bool(media_types.photo),
            document=bool(media_types.document),
            video=bool(media_types.video),
            audio=bool(media_types.audio),
            voice=bool(media_types.voice),
        ),
        extensions=extension_values,
    )


def update_media_settings(session: Session, rule_id: int, payload: MediaSettingsUpdate) -> MediaSettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")

    update_data = payload.dict(exclude_unset=True)
    media_types_update = update_data.pop("media_types", None)
    for field, value in update_data.items():
        setattr(rule, field, value)

    if media_types_update:
        media_types = _get_or_create_media_types(session, rule_id)
        for field, value in media_types_update.items():
            if value is None:
                continue
            setattr(media_types, field, value)

    session.commit()
    return get_media_settings(session, rule_id)


def list_media_extensions(session: Session, rule_id: int) -> List[MediaExtensionOut]:
    rows = (
        session.query(MediaExtensions)
        .filter(MediaExtensions.rule_id == rule_id)
        .order_by(MediaExtensions.id.desc())
        .all()
    )
    return [MediaExtensionOut(id=row.id, extension=row.extension) for row in rows]


def add_media_extension(session: Session, rule_id: int, payload: MediaExtensionCreate) -> List[MediaExtensionOut]:
    row = MediaExtensions(rule_id=rule_id, extension=payload.extension)
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("扩展名已存在")
    return list_media_extensions(session, rule_id)


def delete_media_extension(session: Session, rule_id: int, extension_id: int) -> List[MediaExtensionOut]:
    row = (
        session.query(MediaExtensions)
        .filter(MediaExtensions.rule_id == rule_id, MediaExtensions.id == extension_id)
        .first()
    )
    if not row:
        return list_media_extensions(session, rule_id)
    session.delete(row)
    session.commit()
    return list_media_extensions(session, rule_id)


def get_ai_settings(session: Session, rule_id: int) -> AISettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    models = load_ai_models(type="list")
    return AISettingsOut(
        is_ai=bool(rule.is_ai),
        ai_model=rule.ai_model,
        ai_prompt=rule.ai_prompt,
        enable_ai_upload_image=bool(rule.enable_ai_upload_image),
        is_keyword_after_ai=bool(rule.is_keyword_after_ai),
        is_summary=bool(rule.is_summary),
        summary_time=str(rule.summary_time or ""),
        summary_prompt=rule.summary_prompt,
        is_top_summary=bool(rule.is_top_summary),
        available_models=models,
    )


def update_ai_settings(session: Session, rule_id: int, payload: AISettingsUpdate) -> AISettingsOut:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")

    update_data: Dict[str, Any] = payload.dict(exclude_unset=True)
    if "ai_model" in update_data and not update_data["ai_model"]:
        update_data["ai_model"] = None
    if "summary_time" in update_data and not update_data["summary_time"]:
        update_data["summary_time"] = rule.summary_time

    for field, value in update_data.items():
        setattr(rule, field, value)

    session.commit()
    return get_ai_settings(session, rule_id)
