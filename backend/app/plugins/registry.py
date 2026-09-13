"""插件降级注册表雏形（MVP 原则：外部数据源一律走插件、一律可降级）。

目前仅注册内置 Mock 插件：接口存在、返回标记数据、degraded=True。
后续接入真实供应商（天气/POI/汇率…）时：
  1) 继承 BasePlugin 实现 fetch 并注册；
  2) 未启用或 fetch 失败时调用方必须走降级路径（返回 mock/缓存/提示）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class BasePlugin(ABC):
    key: str = ""
    name: str = ""
    enabled: bool = False

    @abstractmethod
    def status(self) -> dict:
        """插件自检信息（含 degraded 降级标记）。"""


class MockWeatherPlugin(BasePlugin):
    key = "weather"
    name = "天气（Mock 降级）"
    enabled = True

    def status(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "enabled": self.enabled,
            "degraded": True,  # 返回的是演示数据，非真实天气
            "provider": "mock",
        }


class MockPOIPlugin(BasePlugin):
    key = "poi"
    name = "景点/POI（Mock 降级）"
    enabled = True

    def status(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "enabled": self.enabled,
            "degraded": True,
            "provider": "mock",
        }


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}
        for plugin in (MockWeatherPlugin(), MockPOIPlugin()):
            self.register(plugin)

    def register(self, plugin: BasePlugin) -> None:
        self._plugins[plugin.key] = plugin

    def get(self, key: str) -> Optional[BasePlugin]:
        plugin = self._plugins.get(key)
        if plugin is not None and plugin.enabled:
            return plugin
        return None  # 调用方必须降级

    def all_status(self) -> list[dict]:
        return [p.status() for p in self._plugins.values()]


registry = PluginRegistry()
