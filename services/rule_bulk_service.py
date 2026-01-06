from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.models import ForwardRule, Keyword, ReplaceRule


class KeywordBulkCreate(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    is_regex: bool = False
    is_blacklist: bool = True

    @validator("keywords")
    def normalize_keywords(cls, value: List[str]) -> List[str]:
        normalized: List[str] = []
        for item in value or []:
            text = (item or "").strip()
            if not text:
                continue
            normalized.append(text)
        if not normalized:
            raise ValueError("keywords 不能为空")
        return normalized


class BulkResult(BaseModel):
    added: int
    skipped: int


class CopyToRule(BaseModel):
    target_rule_id: int


class ReplaceBulkCreateItem(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=1024)
    content: Optional[str] = Field(default=None, max_length=4096)

    @validator("pattern")
    def strip_pattern(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("pattern 不能为空")
        return trimmed


class ReplaceBulkCreate(BaseModel):
    items: List[ReplaceBulkCreateItem] = Field(default_factory=list)

    @validator("items")
    def validate_items(cls, value: List[ReplaceBulkCreateItem]) -> List[ReplaceBulkCreateItem]:
        if not value:
            raise ValueError("items 不能为空")
        return value


class KeywordAdvancedSettingsOut(BaseModel):
    enable_reverse_blacklist: bool
    enable_reverse_whitelist: bool


class KeywordAdvancedSettingsUpdate(BaseModel):
    enable_reverse_blacklist: Optional[bool]
    enable_reverse_whitelist: Optional[bool]


def _require_rule(session: Session, rule_id: int) -> ForwardRule:
    rule = session.query(ForwardRule).filter(ForwardRule.id == rule_id).first()
    if not rule:
        raise ValueError("规则不存在")
    return rule


def bulk_add_keywords(session: Session, rule_id: int, payload: KeywordBulkCreate) -> BulkResult:
    _require_rule(session, rule_id)
    added = 0
    skipped = 0

    for text in payload.keywords:
        try:
            with session.begin_nested():
                row = Keyword(
                    rule_id=rule_id,
                    keyword=text,
                    is_regex=payload.is_regex,
                    is_blacklist=payload.is_blacklist,
                )
                session.add(row)
                session.flush([row])
            added += 1
        except IntegrityError:
            skipped += 1
    session.commit()
    return BulkResult(added=added, skipped=skipped)


def clear_keywords(session: Session, rule_id: int) -> int:
    _require_rule(session, rule_id)
    deleted = session.query(Keyword).filter(Keyword.rule_id == rule_id).delete(synchronize_session=False)
    session.commit()
    return int(deleted or 0)


def copy_keywords(session: Session, rule_id: int, target_rule_id: int) -> BulkResult:
    _require_rule(session, rule_id)
    _require_rule(session, target_rule_id)
    if rule_id == target_rule_id:
        raise ValueError("不能复制到自身")

    rows = session.query(Keyword).filter(Keyword.rule_id == rule_id).all()
    if not rows:
        return BulkResult(added=0, skipped=0)

    added = 0
    skipped = 0
    for k in rows:
        try:
            with session.begin_nested():
                row = Keyword(
                    rule_id=target_rule_id,
                    keyword=k.keyword,
                    is_regex=bool(k.is_regex),
                    is_blacklist=bool(k.is_blacklist),
                )
                session.add(row)
                session.flush([row])
            added += 1
        except IntegrityError:
            skipped += 1

    session.commit()
    return BulkResult(added=added, skipped=skipped)


def bulk_add_replace_rules(session: Session, rule_id: int, payload: ReplaceBulkCreate) -> BulkResult:
    _require_rule(session, rule_id)
    added = 0
    skipped = 0

    for item in payload.items:
        try:
            with session.begin_nested():
                row = ReplaceRule(rule_id=rule_id, pattern=item.pattern, content=item.content)
                session.add(row)
                session.flush([row])
            added += 1
        except IntegrityError:
            skipped += 1

    session.commit()
    return BulkResult(added=added, skipped=skipped)


def clear_replace_rules(session: Session, rule_id: int) -> int:
    _require_rule(session, rule_id)
    deleted = session.query(ReplaceRule).filter(ReplaceRule.rule_id == rule_id).delete(synchronize_session=False)
    session.commit()
    return int(deleted or 0)


def copy_replace_rules(session: Session, rule_id: int, target_rule_id: int) -> BulkResult:
    _require_rule(session, rule_id)
    _require_rule(session, target_rule_id)
    if rule_id == target_rule_id:
        raise ValueError("不能复制到自身")

    rows = session.query(ReplaceRule).filter(ReplaceRule.rule_id == rule_id).all()
    if not rows:
        return BulkResult(added=0, skipped=0)

    added = 0
    skipped = 0
    for r in rows:
        try:
            with session.begin_nested():
                row = ReplaceRule(rule_id=target_rule_id, pattern=r.pattern, content=r.content)
                session.add(row)
                session.flush([row])
            added += 1
        except IntegrityError:
            skipped += 1

    session.commit()
    return BulkResult(added=added, skipped=skipped)


def export_keywords(session: Session, rule_id: int) -> List[str]:
    _require_rule(session, rule_id)
    rows = session.query(Keyword).filter(Keyword.rule_id == rule_id).order_by(Keyword.id.asc()).all()
    return [
        f"{'REGEX' if row.is_regex else 'TEXT'}\t{'BLACK' if row.is_blacklist else 'WHITE'}\t{row.keyword or ''}"
        for row in rows
    ]


def export_replace_rules(session: Session, rule_id: int) -> List[str]:
    _require_rule(session, rule_id)
    rows = session.query(ReplaceRule).filter(ReplaceRule.rule_id == rule_id).order_by(ReplaceRule.id.asc()).all()
    return [f"{row.pattern}\t=>\t{row.content or ''}" for row in rows]


def get_keyword_advanced_settings(session: Session, rule_id: int) -> KeywordAdvancedSettingsOut:
    rule = _require_rule(session, rule_id)
    return KeywordAdvancedSettingsOut(
        enable_reverse_blacklist=bool(rule.enable_reverse_blacklist),
        enable_reverse_whitelist=bool(rule.enable_reverse_whitelist),
    )


def update_keyword_advanced_settings(
    session: Session, rule_id: int, payload: KeywordAdvancedSettingsUpdate
) -> KeywordAdvancedSettingsOut:
    rule = _require_rule(session, rule_id)
    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)
    session.commit()
    return get_keyword_advanced_settings(session, rule_id)
