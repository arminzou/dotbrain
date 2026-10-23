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
            timeout: float = 600) -> subprocess.CompletedProcess[str]: ...

    def read(self, path: str) -> str: ...

    def teardown(self) -> None: ...


def _kill_tree(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
    proc.kill()


def _writable(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)  # Git writes its objects read-only
    func(path)


class HostBackend:
    """Native Windows: the user home, app data, XDG dirs, runtime homes and data root in a temp sandbox.

    Runtime binaries and ``uv`` are resolved by the caller before the environment is swapped, since
    an install under the live ``%LOCALAPPDATA%`` is invisible once it is.
    """

    def __init__(self, root: Path, *, repo: Path, uv: str):
        self.root = root
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
        install_env = {**os.environ, "UV_TOOL_DIR": str(tools / "venvs"), "UV_TOOL_BIN_DIR": str(tools / "bin")}
        subprocess.run([uv, "tool", "install", "--quiet", "--force", str(repo)], env=install_env, check=True,
                       capture_output=True)
        real = tools / "bin" / "dotbrain.exe"
        Path(self.hook_log).touch()
        # First on PATH, ahead of any live dotbrain: adapters resolve `dotbrain` + PATHEXT from PATH.
        (shim_dir / "dotbrain.cmd").write_text(
            f'@echo off\r\n>>"{self.hook_log}" echo %*\r\n"{real}" %*\r\n', encoding="utf-8")

        env = {name: value for name, value in os.environ.items() if not _DROPPED.search(name)}
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
        env = {**self.env, **(env or {})}
        # Looked up on the sandbox PATH with PATHEXT; Windows would search the live PATH and skip .cmd.
        argv = [shutil.which(argv[0], path=env["PATH"]) or argv[0], *argv[1:]]
        proc = subprocess.Popen(argv, env=env, cwd=cwd or self.checkout,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding="utf-8", errors="replace")
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)  # the runtime's own children would otherwise outlive it
            out, err = proc.communicate()
            raise AssertionError(f"{argv[0]} ran past {timeout} s\n{out[-4000:]}\n{err[-4000:]}") from None
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)

    def read(self, path):
        return Path(path).read_text(encoding="utf-8", errors="replace")

    def teardown(self):
        deadline = time.monotonic() + TEARDOWN_SECONDS
        handler = {"onexc" if sys.version_info >= (3, 12) else "onerror": _writable}
        while True:
            try:
                shutil.rmtree(self.root, **handler)
                return
            except FileNotFoundError:
                return
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(2)
