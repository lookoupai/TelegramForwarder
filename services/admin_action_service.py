from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text


def ensure_actions_table(session: Session) -> None:
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                rule_id INTEGER,
                payload TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT,
                created_at INTEGER NOT NULL,
                processed_at INTEGER
            )
            """
        )
    )
    session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_admin_actions_status_id ON admin_actions(status, id)"
        )
    )
    session.commit()


def enqueue_action(
    session: Session,
    action: str,
    rule_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    ensure_actions_table(session)
    created_at = int(time.time() * 1000)
    payload_text = json.dumps(payload or {}, ensure_ascii=False)
    result = session.execute(
        text(
            """
            INSERT INTO admin_actions(action, rule_id, payload, status, created_at)
            VALUES (:action, :rule_id, :payload, 'pending', :created_at)
            """
        ),
        {
            "action": action,
            "rule_id": rule_id,
            "payload": payload_text,
            "created_at": created_at,
        },
    )
    session.commit()
    return int(result.lastrowid)

