"""应用配置（MVP 骨架级：环境变量覆盖，无 pydantic-settings 依赖）。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "data" / "trip.db")


@dataclass
class Settings:
    db_path: str = os.environ.get("TRIP_DB", _DEFAULT_DB)
    # 前端 dev server 地址（Vite 默认 5173）；生产由同源反代承载，无需 CORS
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.environ.get(
                "TRIP_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",")
            if o.strip()
        ]
    )
    # MVP 无登录系统：以请求头 X-User-Id 作为身份占位（后续替换为真实认证）
    default_user: str = os.environ.get("TRIP_DEFAULT_USER", "u_demo")
