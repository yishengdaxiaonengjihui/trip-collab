"""SQLite 访问层：每个操作独立连接（线程安全），表结构见 init_db。

MVP 骨架级持久化策略：
- trips / members：结构化表
- 引擎状态（事件流+快照+提议+通知）：整包 JSON 存 trip_state.state_json
  升级路径：后续把 state_json 拆成真正的 append-only 事件表 + 提议表，
  引擎 from_dict/to_dict 已为此预留了清晰的边界。
"""

from __future__ import annotations

import sqlite3
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trip_state (
    trip_id    TEXT PRIMARY KEY REFERENCES trips(id),
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS members (
    trip_id TEXT NOT NULL REFERENCES trips(id),
    user_id TEXT NOT NULL,
    role    TEXT NOT NULL DEFAULT 'member',
    PRIMARY KEY (trip_id, user_id)
);
"""


class TripRepo:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        import os

        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ---------- trips ----------

    def create_trip(self, trip_id: str, name: str, created_by: str, created_at: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trips (id, name, created_by, created_at) VALUES (?, ?, ?, ?)",
                (trip_id, name, created_by, created_at),
            )

    def get_trip(self, trip_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
        return dict(row) if row else None

    def list_trips(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM trips ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    # ---------- engine state ----------

    def save_state(self, trip_id: str, state_json: str, updated_at: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trip_state (trip_id, state_json, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(trip_id) DO UPDATE SET state_json = excluded.state_json, "
                "updated_at = excluded.updated_at",
                (trip_id, state_json, updated_at),
            )

    def load_state(self, trip_id: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT state_json FROM trip_state WHERE trip_id = ?", (trip_id,)
            ).fetchone()
        return row["state_json"] if row else None

    # ---------- members ----------

    def add_member(self, trip_id: str, user_id: str, role: str = "member") -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO members (trip_id, user_id, role) VALUES (?, ?, ?)",
                (trip_id, user_id, role),
            )

    def list_members(self, trip_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, role FROM members WHERE trip_id = ? ORDER BY role, user_id",
                (trip_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def set_member_role(self, trip_id: str, user_id: str, role: str) -> Optional[dict]:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE members SET role = ? WHERE trip_id = ? AND user_id = ?",
                (role, trip_id, user_id),
            )
            if cur.rowcount == 0:
                return None
        return {"trip_id": trip_id, "user_id": user_id, "role": role}
