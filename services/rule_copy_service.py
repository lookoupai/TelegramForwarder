from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.models import ForwardRule, Keyword, MediaExtensions, MediaTypes, PushConfig, ReplaceRule, RuleSync


class RuleCopyRequest(BaseModel):
    target_rule_id: int
    copy_rule_fields: bool = True
    copy_keywords: bool = True
    copy_replace_rules: bool = True
    copy_media: bool = True
    copy_push: bool = True
    copy_sync_targets: bool = False
    overwrite: bool = True


class RuleCopyResult(BaseModel):
    ok: bool
    copied_fields: int
    keywords_added: int
    replace_rules_added: int
    media_extensions_added: int
    push_configs_added: int
    sync_targets_added: int


def copy_rule_to(session: Session, source_rule_id: int, payload: RuleCopyRequest) -> RuleCopyResult:
    source = session.query(ForwardRule).filter(ForwardRule.id == source_rule_id).first()
    if not source:
        raise ValueError("源规则不存在")
    target = session.query(ForwardRule).filter(ForwardRule.id == payload.target_rule_id).first()
    if not target:
        raise ValueError("目标规则不存在")
    if target.id == source.id:
        raise ValueError("不能复制到自身")

    copied_fields = 0
    if payload.copy_rule_fields:
        keep_source_chat_id = target.source_chat_id
        keep_target_chat_id = target.target_chat_id

        inspector = inspect(ForwardRule)
        for column in inspector.columns:
            column_name = column.key
            if column_name in (
                "id",
                "source_chat_id",
                "target_chat_id",
            ):
                continue
            setattr(target, column_name, getattr(source, column_name))
            copied_fields += 1

        target.source_chat_id = keep_source_chat_id
        target.target_chat_id = keep_target_chat_id

    keywords_added = 0
    if payload.copy_keywords:
        if payload.overwrite:
            session.query(Keyword).filter(Keyword.rule_id == target.id).delete(synchronize_session=False)
        rows = session.query(Keyword).filter(Keyword.rule_id == source.id).all()
        for row in rows:
            keyword = Keyword(
                rule_id=target.id,
                keyword=row.keyword,
                is_regex=bool(row.is_regex),
                is_blacklist=bool(row.is_blacklist),
            )
            session.add(keyword)
            if payload.overwrite:
                keywords_added += 1
                continue
            try:
                with session.begin_nested():
                    session.flush([keyword])
                keywords_added += 1
            except IntegrityError:
                session.expunge(keyword)

    replace_rules_added = 0
    if payload.copy_replace_rules:
        if payload.overwrite:
            session.query(ReplaceRule).filter(ReplaceRule.rule_id == target.id).delete(synchronize_session=False)
        rows = session.query(ReplaceRule).filter(ReplaceRule.rule_id == source.id).all()
        for row in rows:
            replace_rule = ReplaceRule(rule_id=target.id, pattern=row.pattern, content=row.content)
            session.add(replace_rule)
            if payload.overwrite:
                replace_rules_added += 1
                continue
            try:
                with session.begin_nested():
                    session.flush([replace_rule])
                replace_rules_added += 1
            except IntegrityError:
                session.expunge(replace_rule)

    media_extensions_added = 0
    if payload.copy_media:
        if payload.overwrite:
            session.query(MediaTypes).filter(MediaTypes.rule_id == target.id).delete(synchronize_session=False)
            session.query(MediaExtensions).filter(MediaExtensions.rule_id == target.id).delete(synchronize_session=False)

        source_media_types = session.query(MediaTypes).filter(MediaTypes.rule_id == source.id).first()
        if source_media_types:
            if payload.overwrite:
                session.add(
                    MediaTypes(
                        rule_id=target.id,
                        photo=bool(source_media_types.photo),
                        document=bool(source_media_types.document),
                        video=bool(source_media_types.video),
                        audio=bool(source_media_types.audio),
                        voice=bool(source_media_types.voice),
                    )
                )
            else:
                target_media_types = session.query(MediaTypes).filter(MediaTypes.rule_id == target.id).first()
                if not target_media_types:
                    session.add(
                        MediaTypes(
                            rule_id=target.id,
                            photo=bool(source_media_types.photo),
                            document=bool(source_media_types.document),
                            video=bool(source_media_types.video),
                            audio=bool(source_media_types.audio),
                            voice=bool(source_media_types.voice),
                        )
                    )
                else:
                    target_media_types.photo = bool(source_media_types.photo)
                    target_media_types.document = bool(source_media_types.document)
                    target_media_types.video = bool(source_media_types.video)
                    target_media_types.audio = bool(source_media_types.audio)
                    target_media_types.voice = bool(source_media_types.voice)

        rows = session.query(MediaExtensions).filter(MediaExtensions.rule_id == source.id).all()
        for row in rows:
            ext = MediaExtensions(rule_id=target.id, extension=row.extension)
            session.add(ext)
            if payload.overwrite:
                media_extensions_added += 1
                continue
            try:
                with session.begin_nested():
                    session.flush([ext])
                media_extensions_added += 1
            except IntegrityError:
                session.expunge(ext)

    push_configs_added = 0
    if payload.copy_push:
        if payload.overwrite:
            session.query(PushConfig).filter(PushConfig.rule_id == target.id).delete(synchronize_session=False)
        rows = session.query(PushConfig).filter(PushConfig.rule_id == source.id).all()
        for row in rows:
            session.add(
                PushConfig(
                    rule_id=target.id,
                    enable_push_channel=bool(row.enable_push_channel),
                    push_channel=row.push_channel,
                    media_send_mode=row.media_send_mode,
                )
            )
            push_configs_added += 1

    sync_targets_added = 0
    if payload.copy_sync_targets:
        if payload.overwrite:
            session.query(RuleSync).filter(RuleSync.rule_id == target.id).delete(synchronize_session=False)
        rows = session.query(RuleSync).filter(RuleSync.rule_id == source.id).all()
        for row in rows:
            if row.sync_rule_id == target.id:
                continue
            sync_row = RuleSync(rule_id=target.id, sync_rule_id=row.sync_rule_id)
            session.add(sync_row)
            if payload.overwrite:
                sync_targets_added += 1
                continue
            try:
                with session.begin_nested():
                    session.flush([sync_row])
                sync_targets_added += 1
            except IntegrityError:
                session.expunge(sync_row)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("复制失败：目标规则存在冲突数据（唯一约束）")

    return RuleCopyResult(
        ok=True,
        copied_fields=copied_fields,
        keywords_added=keywords_added,
        replace_rules_added=replace_rules_added,
        media_extensions_added=media_extensions_added,
        push_configs_added=push_configs_added,
        sync_targets_added=sync_targets_added,
    )
