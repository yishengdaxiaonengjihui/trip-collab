"""插件状态路由。"""

from __future__ import annotations

from fastapi import APIRouter

from ..plugins.registry import registry

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("")
def list_plugins():
    return {"plugins": registry.all_status()}
