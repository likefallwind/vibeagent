from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import random
from threading import Event, RLock, Thread
from typing import Callable

from .marketplace_store import (
    list_installed_marketplaces,
    update_marketplace,
    update_marketplace_plugin,
)
from .plugin_store import list_installed_plugins


MAX_AUTO_UPDATE_DELAY_SECONDS = 600.0


@dataclass(frozen=True)
class PluginAutoUpdateNotification:
    marketplace: str
    updated_plugins: tuple[str, ...] = ()
    unchanged_plugins: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.updated_plugins)


class PluginAutoUpdateRuntime:
    def __init__(
        self,
        project_root: Path,
        *,
        delay_seconds: float | None = None,
        delay_factory: Callable[[], float] | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.delay_seconds = (
            max(0.0, min(delay_seconds, MAX_AUTO_UPDATE_DELAY_SECONDS))
            if delay_seconds is not None
            else (delay_factory or _random_delay)()
        )
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._notifications: list[PluginAutoUpdateNotification] = []

    def start(self) -> bool:
        if self._thread is not None or not plugin_auto_updates_enabled():
            return False
        try:
            marketplaces = list_installed_marketplaces(self.project_root)
        except (OSError, UnicodeError, ValueError) as error:
            self._append_notification(
                PluginAutoUpdateNotification(
                    marketplace="startup",
                    errors=(f"configuration: {type(error).__name__}: {error}",),
                )
            )
            return False
        if not any(item.auto_update and item.error is None for item in marketplaces):
            return False
        self._thread = Thread(
            target=self._run,
            name="vibeagent-plugin-auto-update",
            daemon=True,
        )
        self._thread.start()
        return True

    def collect_notifications(self) -> list[PluginAutoUpdateNotification]:
        with self._lock:
            notifications = list(self._notifications)
            self._notifications.clear()
        return notifications

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.2)

    def _run(self) -> None:
        if self._stop.wait(self.delay_seconds):
            return
        try:
            marketplaces = [
                item
                for item in list_installed_marketplaces(self.project_root)
                if item.auto_update and item.error is None
            ]
        except (OSError, UnicodeError, ValueError) as error:
            self._append_notification(
                PluginAutoUpdateNotification(
                    marketplace="runtime",
                    errors=(f"configuration: {type(error).__name__}: {error}",),
                )
            )
            return
        for marketplace in marketplaces:
            if self._stop.is_set():
                return
            try:
                notification = auto_update_marketplace(self.project_root, marketplace.name)
            except Exception as error:  # pragma: no cover - isolate the background worker.
                notification = PluginAutoUpdateNotification(
                    marketplace=marketplace.name,
                    errors=(f"unexpected: {type(error).__name__}: {error}",),
                )
            self._append_notification(notification)

    def _append_notification(self, notification: PluginAutoUpdateNotification) -> None:
        with self._lock:
            self._notifications.append(notification)


def auto_update_marketplace(
    project_root: Path,
    name: str,
) -> PluginAutoUpdateNotification:
    try:
        update_marketplace(project_root, name)
    except (OSError, UnicodeError, ValueError) as error:
        return PluginAutoUpdateNotification(
            marketplace=name,
            errors=(f"marketplace refresh: {type(error).__name__}: {error}",),
        )
    plugins = [
        item
        for item in list_installed_plugins(project_root)
        if item.marketplace == name and item.error is None
    ]
    updated: list[str] = []
    unchanged: list[str] = []
    errors: list[str] = []
    for plugin in plugins:
        try:
            result = update_marketplace_plugin(project_root, plugin.name, current=plugin)
        except (OSError, UnicodeError, ValueError) as error:
            errors.append(f"{plugin.name}: {type(error).__name__}: {error}")
            continue
        (updated if result.updated else unchanged).append(plugin.name)
    return PluginAutoUpdateNotification(
        marketplace=name,
        updated_plugins=tuple(updated),
        unchanged_plugins=tuple(unchanged),
        errors=tuple(errors),
    )


def format_plugin_auto_update_notification(
    notification: PluginAutoUpdateNotification,
) -> str:
    if notification.updated_plugins:
        plugins = ", ".join(notification.updated_plugins)
        text = (
            f"Plugin auto-update refreshed {notification.marketplace}: updated {plugins}. "
            "Run /reload-plugins to activate the new version."
        )
    else:
        text = f"Plugin auto-update checked {notification.marketplace}; no plugin updates."
    if notification.errors:
        text += " Errors: " + "; ".join(notification.errors)
    return text


def plugin_auto_updates_enabled() -> bool:
    disabled = _truthy(os.environ.get("DISABLE_AUTOUPDATER"))
    forced = _truthy(os.environ.get("FORCE_AUTOUPDATE_PLUGINS"))
    return not disabled or forced


def _random_delay() -> float:
    return random.uniform(0.0, MAX_AUTO_UPDATE_DELAY_SECONDS)


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "MAX_AUTO_UPDATE_DELAY_SECONDS",
    "PluginAutoUpdateNotification",
    "PluginAutoUpdateRuntime",
    "auto_update_marketplace",
    "format_plugin_auto_update_notification",
    "plugin_auto_updates_enabled",
]
