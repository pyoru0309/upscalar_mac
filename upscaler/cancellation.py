from __future__ import annotations

import threading
from typing import Optional


class UpscaleCancelled(Exception):
    """Raised when a running upscale job is cancelled."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise UpscaleCancelled("キャンセルされました。")


_lock = threading.Lock()
_current: Optional[CancelToken] = None


def start_token() -> CancelToken:
    global _current
    token = CancelToken()
    with _lock:
        _current = token
    return token


def cancel_current() -> None:
    with _lock:
        token = _current
    if token is not None:
        token.cancel()


def clear_current(token: CancelToken) -> None:
    global _current
    with _lock:
        if _current is token:
            _current = None
