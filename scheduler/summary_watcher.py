from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Dict, Tuple

from models.models import ForwardRule, get_session

logger = logging.getLogger(__name__)


async def watch_summary_settings(scheduler, poll_interval_seconds: int = 5) -> None:
    """
    监听 DB 中与 AI 总结相关的配置变更，并在主进程内热更新调度任务。

    说明：
    - Web 管理页面运行在独立进程，无法直接调用主进程内存中的 scheduler；
      因此通过主进程轮询 DB 变更来触发 schedule_rule()。
    - 仅处理“是否启用总结/总结时间/提示词/是否置顶”等字段的变更。
    """
    last_signatures: Dict[int, Tuple[bool, str, str, bool]] = {}
    initialized = False

    while True:
        try:
            session = get_session()
            try:
                rows = (
                    session.query(
                        ForwardRule.id,
                        ForwardRule.is_summary,
                        ForwardRule.summary_time,
                        ForwardRule.summary_prompt,
                        ForwardRule.is_top_summary,
                    )
                    .order_by(ForwardRule.id.asc())
                    .all()
                )
            finally:
                session.close()

            current_ids = set()
            for rule_id, is_summary, summary_time, summary_prompt, is_top_summary in rows:
                current_ids.add(rule_id)
                signature = (
                    bool(is_summary),
                    str(summary_time or ""),
                    str(summary_prompt or ""),
                    bool(is_top_summary),
                )
                if not initialized:
                    last_signatures[rule_id] = signature
                    continue

                if last_signatures.get(rule_id) == signature:
                    continue

                last_signatures[rule_id] = signature
                logger.info(
                    "检测到总结配置变更，准备热更新调度任务：rule_id=%s is_summary=%s summary_time=%s",
                    rule_id,
                    bool(is_summary),
                    summary_time,
                )
                await scheduler.schedule_rule(
                    SimpleNamespace(
                        id=rule_id,
                        is_summary=bool(is_summary),
                        summary_time=str(summary_time or "00:00"),
                    )
                )

            if initialized:
                removed = set(last_signatures.keys()) - current_ids
                for removed_id in removed:
                    last_signatures.pop(removed_id, None)
                    if getattr(scheduler, "tasks", None) and removed_id in scheduler.tasks:
                        logger.info("规则已删除，取消其总结任务：rule_id=%s", removed_id)
                        await scheduler.schedule_rule(
                            SimpleNamespace(id=removed_id, is_summary=False, summary_time="00:00")
                        )

            initialized = True
            await asyncio.sleep(poll_interval_seconds)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("SummaryWatcher 运行异常：%s", str(exc))
            logger.exception(exc)
            await asyncio.sleep(poll_interval_seconds)

