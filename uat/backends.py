"""Backends: a disposable environment for an agent runtime and a way to run commands in it.

Journeys use only ``run``, ``read`` and ``teardown`` and the sandbox paths as the backend sees them,
so a container backend can implement the same interface.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Protocol

# Live variables that could carry a credential or aim a runtime or dotbrain at live state; the
# sandbox environment drops them, and a journey passes its one credential to the runtime alone.
_DROPPED = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|AUTH|BASE_URL|^OPENCODE_|^XDG_|^DOTBRAIN_|^UAT_|^PI_|^CURSOR_|^HERMES_",
                      re.I)
TEARDOWN_SECONDS = 60  # a detached sync still running against the unreachable remote holds the data root


class Backend(Protocol):
    home: str  # the sandbox user home
    data_root: str  # the sandbox data root (DOTBRAIN_HOME)
    checkout: str  # the wired project checkout
    hook_log: str  # where the recording shim appends each `dotbrain` call
    python: str  # an interpreter that can run uat/prepare.py

    def run(self, argv: list[str], *, env: dict[str, str] | None = None, cwd: str | None = None,
            timeout: float = 600) -> subprocess.CompletedProcess[str]:
        """Run ``argv``; ``env`` holds credentials, given to this process only and redacted from its output."""

    def read(self, path: str) -> str: ...

    def teardown(self) -> None: ...


def sanitized(environ) -> dict[str, str]:
    """``environ`` without anything that could carry a credential or aim at live runtime or data-root state."""
    return {name: value for name, value in environ.items() if not _DROPPED.search(name)}


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


def shim_script(log: str, real: str, credential_vars) -> str:
    """The recording `dotbrain` shim: drop the credentials, log the argv, run the real CLI.

    The runtime's credential stops here, so dotbrain, its detached sync and git never see it.
    """
    lines = ["@echo off", "setlocal", *(f'set "{name}="' for name in credential_vars),
             f'>>"{log}" echo %*', f'"{real}" %*']
    return "\r\n".join(lines) + "\r\n"


def run_process(argv, *, env, cwd, timeout, secrets=()):
    """``subprocess.run`` that kills the whole tree on timeout and redacts ``secrets`` from the output."""
    # Looked up on the given PATH with PATHEXT; Windows would search the live PATH and skip .cmd.
    argv = [shutil.which(argv[0], path=env.get("PATH")) or argv[0], *argv[1:]]
    proc = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)  # the runtime's own children would otherwise outlive it
        out, err = proc.communicate()
        raise AssertionError(redact(f"{argv[0]} ran past {timeout} s\n{out[-4000:]}\n{err[-4000:]}", secrets)) from None
    return subprocess.CompletedProcess(argv, proc.returncode, redact(out, secrets), redact(err, secrets))


def _kill_tree(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
    proc.kill()


def _writable(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)  # Git writes its objects read-only
    func(path)


def remove_tree(root: Path, seconds: float = TEARDOWN_SECONDS) -> None:
    """Remove ``root``, retrying while a detached sync still holds files in it."""
    deadline = time.monotonic() + seconds
    handler = {"onexc" if sys.version_info >= (3, 12) else "onerror": _writable}
    while True:
        try:
            shutil.rmtree(root, **handler)
            return
        except FileNotFoundError:
            return
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)


class HostBackend:
    """Native Windows: the user home, app data, XDG dirs, runtime homes and data root in a temp sandbox.

    Runtime binaries and ``uv`` are resolved by the caller before the environment is swapped, since
    an install under the live ``%LOCALAPPDATA%`` is invisible once it is. ``credential_vars`` are
    the variables the shim removes before running dotbrain.
    """

    def __init__(self, root: Path, *, repo: Path, uv: str, credential_vars=()):
        self.root = root
        try:
            self._build(root, repo, uv, credential_vars)
        except BaseException:
            remove_tree(root)
            raise

    def _build(self, root, repo, uv, credential_vars):
        home = root / "home"
        self.home = str(home)
        self.data_root = str(home / "dotbrain")
        self.checkout = str(root / "checkout")
        shim_dir, tools = root / "shim", root / "tools"
        self.hook_log = str(root / "dotbrain-calls.log")
        self.python = sys.executable
        for folder in (home / "AppData" / "Roaming", home / "AppData" / "Local", shim_dir, Path(self.checkout)):
            folder.mkdir(parents=True, exist_ok=True)

        # The real CLI, from the checkout under test, into the sandbox rather than the live uv tool dir.
        install_env = {**sanitized(os.environ), "UV_TOOL_DIR": str(tools / "venvs"),
                       "UV_TOOL_BIN_DIR": str(tools / "bin")}
        subprocess.run([uv, "tool", "install", "--quiet", "--force", str(repo)], env=install_env, check=True,
                       capture_output=True)
        real = tools / "bin" / "dotbrain.exe"
        Path(self.hook_log).touch()
        # First on PATH, ahead of any live dotbrain: adapters resolve `dotbrain` + PATHEXT from PATH.
        (shim_dir / "dotbrain.cmd").write_text(shim_script(self.hook_log, str(real), credential_vars),
                                               encoding="utf-8")

        env = sanitized(os.environ)
        env.update({
            "PATH": os.pathsep.join([str(shim_dir), os.environ.get("PATH", "")]),
            "HOME": self.home, "USERPROFILE": self.home,
            "APPDATA": str(home / "AppData" / "Roaming"), "LOCALAPPDATA": str(home / "AppData" / "Local"),
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local" / "share"),
            "XDG_STATE_HOME": str(home / ".local" / "state"), "XDG_CACHE_HOME": str(home / ".cache"),
            "DOTBRAIN_HOME": self.data_root,
            # Runtime homes default below the swapped home; set the relocatable ones explicitly.
            "PI_CODING_AGENT_DIR": str(home / ".pi" / "agent"), "HERMES_HOME": str(home / ".hermes"),
            "OPENCODE_TEST_HOME": self.home, "OPENCODE_DISABLE_CLAUDE_CODE": "1", "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "GIT_AUTHOR_NAME": "dotbrain uat", "GIT_AUTHOR_EMAIL": "uat@dotbrain.invalid",
            "GIT_COMMITTER_NAME": "dotbrain uat", "GIT_COMMITTER_EMAIL": "uat@dotbrain.invalid",
            "GIT_TERMINAL_PROMPT": "0",
        })
        self.env = env

    def run(self, argv, *, env=None, cwd=None, timeout=600):
        # Values passed in `env` are credentials: only this process gets them, and output never shows them.
        return run_process(argv, env={**self.env, **(env or {})}, cwd=cwd or self.checkout, timeout=timeout,
                           secrets=(env or {}).values())

    def read(self, path):
        return Path(path).read_text(encoding="utf-8", errors="replace")

    def teardown(self):
        remove_tree(self.root)


