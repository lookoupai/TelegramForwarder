from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import text

from models.models import get_session
from services.admin_action_service import ensure_actions_table

logger = logging.getLogger(__name__)


async def run_admin_action_worker(
    scheduler: Any,
    db_ops: Any,
    chat_updater: Any = None,
    poll_interval_seconds: int = 2,
    batch_size: int = 10,
) -> None:
    """
    主进程内执行后台动作（跨进程热更新/触发），供 Web 管理页面使用。

    当前支持：
    - summary_now：立即执行某规则总结
    - summary_all_now：立即执行所有启用总结的规则
    - ufb_sync：立即同步某规则的关键字配置到 UFB
    - update_chats_now：立即更新数据库中聊天名称
    """
    while True:
        try:
            session = get_session()
            try:
                ensure_actions_table(session)
                rows = session.execute(
                    text(
                        """
                        SELECT id, action, rule_id, payload
                        FROM admin_actions
                        WHERE status = 'pending'
                        ORDER BY id ASC
                        LIMIT :limit
                        """
                    ),
                    {"limit": batch_size},
                ).fetchall()
            finally:
                session.close()

            if not rows:
                await asyncio.sleep(poll_interval_seconds)
                continue

            for row in rows:
                action_id = int(row[0])
                action = str(row[1])
                rule_id = row[2]
                payload_text = row[3] or "{}"
                payload: Dict[str, Any] = {}
                try:
                    payload = json.loads(payload_text)
                except Exception:
                    payload = {}

                await _process_one_action(
                    action_id=action_id,
                    action=action,
                    rule_id=int(rule_id) if rule_id is not None else None,
                    payload=payload,
                    scheduler=scheduler,
                    db_ops=db_ops,
                    chat_updater=chat_updater,
                )

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("AdminActionWorker 运行异常：%s", str(exc))
            logger.exception(exc)
            await asyncio.sleep(poll_interval_seconds)


async def _process_one_action(
    *,
    action_id: int,
    action: str,
    rule_id: Optional[int],
    payload: Dict[str, Any],
    scheduler: Any,
    db_ops: Any,
    chat_updater: Any,
) -> None:
    processed_at = int(time.time() * 1000)

    session = get_session()
    try:
        ensure_actions_table(session)
        session.execute(
            text(
                """
                UPDATE admin_actions
                SET status = 'processing', processed_at = :processed_at, error = NULL
                WHERE id = :id AND status = 'pending'
                """
            ),
            {"id": action_id, "processed_at": processed_at},
        )
        session.commit()
    finally:
        session.close()

    try:
        if action == "summary_now":
            if not rule_id:
                raise ValueError("rule_id 不能为空")
            if not scheduler or not hasattr(scheduler, "_execute_summary"):
                raise RuntimeError("scheduler 未就绪")
            await scheduler._execute_summary(rule_id, is_now=True)

        elif action == "summary_all_now":
            if not scheduler or not hasattr(scheduler, "execute_all_summaries"):
                raise RuntimeError("scheduler 未就绪")
            await scheduler.execute_all_summaries()

        elif action == "ufb_sync":
            if not rule_id:
                raise ValueError("rule_id 不能为空")
            if not db_ops or not hasattr(db_ops, "sync_to_server"):
                raise RuntimeError("db_ops 未就绪")
            db_session = get_session()
            try:
                await db_ops.sync_to_server(db_session, rule_id)
            finally:
                db_session.close()

        elif action == "update_chats_now":
            if not chat_updater or not hasattr(chat_updater, "_update_all_chats"):
                raise RuntimeError("chat_updater 未就绪")
            await chat_updater._update_all_chats()

        else:
            raise ValueError(f"未知 action: {action}")

        _mark_action_done(action_id)
    except Exception as exc:
        _mark_action_error(action_id, str(exc))


def _mark_action_done(action_id: int) -> None:
    session = get_session()
    try:
        ensure_actions_table(session)
        session.execute(
            text("UPDATE admin_actions SET status='done', error=NULL WHERE id=:id"),
            {"id": action_id},
        )
        session.commit()
    finally:
        session.close()


def _mark_action_error(action_id: int, error: str) -> None:
    session = get_session()
    try:
        ensure_actions_table(session)
        session.execute(
            text("UPDATE admin_actions SET status='error', error=:error WHERE id=:id"),
            {"id": action_id, "error": error[:2000]},
        )
        session.commit()
    finally:
        session.close()
