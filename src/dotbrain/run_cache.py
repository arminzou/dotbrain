"""Facts that hold for one command run, looked up once instead of once per project.

Caching is active only inside ``scope()``, so library callers and tests outside a command
see every lookup run fresh. Code that changes a cached fact calls ``forget`` or ``clear``.
"""
from __future__ import annotations

import contextlib
import functools
import threading
from collections.abc import Callable, Hashable, Iterator
from typing import TypeVar

T = TypeVar("T")

# One dict shared by worker threads: doctor checks projects in parallel within one scope.
_store: dict[Hashable, object] | None = None
_locks: dict[Hashable, threading.Lock] = {}
_guard = threading.Lock()


@contextlib.contextmanager
def scope() -> Iterator[None]:
    """Cache lookups until the outermost scope exits."""
    global _store
    if _store is not None:
        yield
        return
    _store = {}
    try:
        yield
    finally:
        _store = None
        _locks.clear()


def get(key: Hashable, compute: Callable[[], T]) -> T:
    store = _store
    if store is None:
        return compute()
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:  # threads asking for the same fact wait for one lookup
        if key not in store:
            store[key] = compute()
        return store[key]  # type: ignore[return-value]


def memo(fn: Callable[..., T]) -> Callable[..., T]:
    """Cache ``fn`` by its arguments within a scope."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return get((fn.__module__, fn.__qualname__, args, tuple(sorted(kwargs.items()))), lambda: fn(*args, **kwargs))
    return wrapper


def forget(match: Callable[[Hashable, object], bool]) -> None:
    """Drop entries for which ``match(key, value)`` holds."""
    store = _store
    if store is not None:
        for key in [key for key, value in list(store.items()) if match(key, value)]:
            store.pop(key, None)


def clear() -> None:
    if _store is not None:
        _store.clear()
