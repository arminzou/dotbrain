"""Backends: a disposable environment for an agent runtime and a way to run commands in it.

Journeys use only ``run``, ``read`` and ``teardown`` and the sandbox paths as the backend sees them,
so the host and container backends share every journey.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Protocol

# Live variables that could carry a credential or aim a runtime or dotbrain at live state; the
# sandbox environment drops them, and a journey passes its one credential to the runtime alone.
_DROPPED = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|AUTH|BASE_URL|^OPENCODE_|^XDG_|^DOTBRAIN_|^UAT_|^PI_|^CURSOR_|^HERMES_",
                      re.I)
TEARDOWN_SECONDS = 60  # a detached sync still running against the unreachable remote holds the data root
HERE = Path(__file__).resolve().parent


class Backend(Protocol):
    home: str  # the sandbox user home
    data_root: str  # the sandbox data root (DOTBRAIN_HOME)
    checkout: str  # the wired project checkout
    hook_log: str  # where the recording shim appends each `dotbrain` call
    python: str  # an interpreter that can run uat/prepare.py
    prepare: str  # uat/prepare.py as this backend sees it

    def run(self, argv: list[str], *, env: dict[str, str] | None = None, cwd: str | None = None,
            timeout: float = 600) -> subprocess.CompletedProcess[str]:
        """Run ``argv``; ``env`` holds credentials, given to this process only and redacted from its output."""

    def start(self) -> None:
        """Create the sandbox; on failure, remove what was made. Construction itself creates nothing,
        so a caller holds the cleanup handle before anything exists."""

    def read(self, path: str) -> str: ...

    def leaks(self, secret: str) -> list[str]:
        """Files in the sandbox that contain ``secret``."""

    def teardown(self) -> None:
        """Remove the sandbox, whether or not ``start`` finished; safe to call again."""


def sanitized(environ) -> dict[str, str]:
    """``environ`` without anything that could carry a credential or aim at live runtime or data-root state."""
    return {name: value for name, value in environ.items() if not _DROPPED.search(name)}


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


# The host's recording `dotbrain` shim is an .exe: Node's spawn without a shell (Pi's adapter) finds
# only `<name>.exe` or `.com`, and a .cmd would pass the arguments through cmd.exe, which reads `&`,
# `^` and `%VAR%` in them as syntax. It logs the argv, drops the credentials, and runs the real CLI
# with each argument re-quoted for the Windows argv parser, so every argument arrives literally.
SHIM_SOURCE = r"""
using System; using System.Diagnostics; using System.IO; using System.Text; using System.Threading;
class Shim {
    static string Quote(string arg) {
        if (arg.Length > 0 && arg.IndexOfAny(new[] { ' ', '\t', '\n', '\v', '"' }) < 0) return arg;
        var quoted = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in arg) {
            if (c == '\\') { slashes++; continue; }
            quoted.Append('\\', c == '"' ? slashes * 2 + 1 : slashes).Append(c);
            slashes = 0;
        }
        return quoted.Append('\\', slashes * 2).Append('"').ToString();
    }
    static int Main() {
        string[] argv = Environment.GetCommandLineArgs();
        string[] args = new string[argv.Length - 1];
        Array.Copy(argv, 1, args, 0, args.Length);
        for (int attempt = 0; ; attempt++) {
            try { File.AppendAllText(__LOG__, string.Join(" ", args) + "\n"); break; }
            catch (IOException) { if (attempt > 50) throw; Thread.Sleep(20); }  // a concurrent call holds the log
        }
        var info = new ProcessStartInfo(__REAL__, string.Join(" ", Array.ConvertAll(args, Quote)));
        info.UseShellExecute = false;
        foreach (string name in new string[] { __CREDENTIALS__ }) info.EnvironmentVariables.Remove(name);
        using (var child = Process.Start(info)) { child.WaitForExit(); return child.ExitCode; }
    }
}
"""


def build_shim(shim_dir: Path, log: str, real: str, credential_vars) -> None:
    """Compile the recording shim to ``shim_dir/dotbrain.exe`` with Windows' own C# compiler.

    The runtime's credential stops here, so dotbrain, its detached sync and git never see it.
    """
    def literal(text):
        return '@"' + str(text).replace('"', '""') + '"'

    source = (SHIM_SOURCE.replace("__LOG__", literal(log)).replace("__REAL__", literal(real))
              .replace("__CREDENTIALS__", ", ".join(map(literal, credential_vars))))
    (shim_dir / "shim.cs").write_text(source, encoding="utf-8")
    csc = Path(os.environ.get("WINDIR", r"C:\Windows"), "Microsoft.NET", "Framework64", "v4.0.30319", "csc.exe")
    subprocess.run([str(csc), "/nologo", f"/out:{shim_dir / 'dotbrain.exe'}", str(shim_dir / "shim.cs")],
                   env=sanitized(os.environ), check=True, capture_output=True)


def sh_shim_script(log: str, real: str, credential_vars) -> str:
    """The host's recording shim as a POSIX ``sh`` script, for the container."""
    lines = ["#!/bin/sh", *(f"unset {name}" for name in credential_vars),
             f'printf "%s\\n" "$*" >> {shlex.quote(log)}', f'exec {shlex.quote(real)} "$@"']
    return "\n".join(lines) + "\n"


def leaks(root: Path, secret: str) -> list[str]:
    """Files below ``root`` that contain ``secret``."""
    needle = secret.encode()
    found = []
    for top, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(top, name)
            try:
                with open(path, "rb") as handle:
                    if needle in handle.read():
                        found.append(path)
            except OSError:
                continue
    return found


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
        self._args = (repo, uv, credential_vars)

    def start(self):
        try:
            self._build(self.root, *self._args)
        except BaseException:
            with suppress(Exception):  # the caller's teardown retries and reports a failed removal
                self.teardown()
            raise

    def _build(self, root, repo, uv, credential_vars):
        home = root / "home"
        self.home = str(home)
        self.data_root = str(home / "dotbrain")
        self.checkout = str(root / "checkout")
        shim_dir, tools = root / "shim", root / "tools"
        self.hook_log = str(root / "dotbrain-calls.log")
        self.python = sys.executable
        self.prepare = str(HERE / "prepare.py")
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
        build_shim(shim_dir, self.hook_log, str(real), credential_vars)

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
            "PI_SKIP_VERSION_CHECK": "1", "PI_TELEMETRY": "0",
            "OPENCODE_TEST_HOME": self.home, "OPENCODE_DISABLE_CLAUDE_CODE": "1", "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "AGENT_CLI_CREDENTIAL_STORE": "memory",  # Cursor keeps its login in memory, not a store or file
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

    def leaks(self, secret):
        return leaks(self.root, secret)

    def teardown(self):
        remove_tree(self.root)


# Where the image puts things (see uat/Dockerfile).
CONTAINER_LOG = "/work/dotbrain-calls.log"
CONTAINER_DOTBRAIN = "/opt/dotbrain/bin/dotbrain"


def docker_problem() -> str | None:
    """Why the container backend cannot run here, or ``None``."""
    from testcontainers.core.docker_client import DockerClient

    try:
        DockerClient().client.ping()
    except Exception as error:  # noqa: BLE001 - any failure means no usable Docker
        return f"start Docker for the container backend ({type(error).__name__})"
    return None


@contextmanager
def _locked(path: Path, seconds: float = 1800):
    """An exclusive lock file; every xdist worker sees the same ``path``."""
    deadline = time.monotonic() + seconds
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise TimeoutError(f"{path} still held after {seconds} s") from None
            time.sleep(2)
    try:
        yield
    finally:
        os.close(fd)
        os.unlink(path)


def container_image(repo: Path, uv: str, lock_dir: Path, credential_vars) -> tuple[str, str]:
    """The UAT image for the checkout's current state, built once and shared: ``(tag, image id)``.

    The tag is a hash of the Dockerfile, the checkout's commit and its uncommitted diff, so workers
    and later runs on the same state reuse it, and the first worker builds it under a lock.
    """
    from testcontainers.core.docker_client import DockerClient
    from testcontainers.core.image import DockerImage

    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).stdout

    dockerfile = HERE / "Dockerfile"
    key = hashlib.sha256(dockerfile.read_bytes() + git("rev-parse", "HEAD") + git("diff", "HEAD")).hexdigest()[:16]
    tag = f"dotbrain-uat:{key}"
    with _locked(lock_dir / f"dotbrain-uat-{key}.lock"):
        images = DockerClient().client.images
        if images.list(name=tag):
            return tag, images.get(tag).id
        with tempfile.TemporaryDirectory() as context:
            subprocess.run([uv, "build", "--wheel", "--quiet", "--out-dir", context, str(repo)],
                           env=sanitized(os.environ), check=True, capture_output=True)
            shutil.copy(dockerfile, context)
            shutil.copy(HERE / "prepare.py", context)
            Path(context, "dotbrain").write_text(sh_shim_script(CONTAINER_LOG, CONTAINER_DOTBRAIN, credential_vars),
                                                 encoding="utf-8", newline="\n")
            image = DockerImage(context, tag=tag, clean_up=False).build()
            return tag, image.get_wrapped_image().id


class ContainerBackend:
    """A container from the UAT image: its whole filesystem is the sandbox, and teardown removes it.

    Credentials reach a process only through the Docker API's exec environment, never the
    container's own environment, the image, or a command line.
    """

    home = "/root"
    data_root = "/root/dotbrain"
    checkout = "/work/checkout"
    hook_log = CONTAINER_LOG
    python = "python3"
    prepare = "/opt/uat/prepare.py"

    def __init__(self, image: str):
        from testcontainers.core.container import DockerContainer

        self._container = DockerContainer(image).with_command("sleep infinity").with_envs(
            DOTBRAIN_HOME=self.data_root, OPENCODE_DISABLE_CLAUDE_CODE="1", OPENCODE_DISABLE_AUTOUPDATE="1",
            PI_SKIP_VERSION_CHECK="1", PI_TELEMETRY="0",
            AGENT_CLI_CREDENTIAL_STORE="memory",
            GIT_AUTHOR_NAME="dotbrain uat", GIT_AUTHOR_EMAIL="uat@dotbrain.invalid",
            GIT_COMMITTER_NAME="dotbrain uat", GIT_COMMITTER_EMAIL="uat@dotbrain.invalid", GIT_TERMINAL_PROMPT="0")
        self._started = False

    def start(self):
        try:
            self._container.start()
        except BaseException:
            with suppress(Exception):  # the caller's teardown retries and reports a failed removal
                self.teardown()
            raise
        self._started = True

    def _exec(self, argv, env=None, cwd=None):
        code, (out, err) = self._container.get_wrapped_container().exec_run(
            argv, environment=env or None, workdir=cwd or self.checkout, demux=True)
        return code, (out or b"").decode("utf-8", "replace"), (err or b"").decode("utf-8", "replace")

    def run(self, argv, *, env=None, cwd=None, timeout=600):
        secrets = list((env or {}).values())
        # OpenCode exits before a pipe drains and loses all output past 64 KiB, so the command writes
        # to files instead: in memory (/dev/shm) and unlinked before it starts, so no path ever holds
        # its raw output, which may carry a credential until it is redacted below.
        # `timeout` signals the command's whole process group; the container's removal ends the rest.
        script = ('o=$(mktemp -p /dev/shm) e=$(mktemp -p /dev/shm); exec 3>"$o" 4<"$o" 5>"$e" 6<"$e"; '
                  'rm -f "$o" "$e"; timeout -k 5 "$0" "$@" >&3 2>&5; code=$?; cat <&4; cat <&6 >&2; exit $code')
        code, out, err = self._exec(["sh", "-c", script, str(math.ceil(timeout)), *argv], env, cwd)
        out, err = redact(out, secrets), redact(err, secrets)
        if code in (124, 137):
            raise AssertionError(redact(f"{argv[0]} ran past {timeout} s\n{out[-4000:]}\n{err[-4000:]}", secrets))
        return subprocess.CompletedProcess(argv, code, out, err)

    def read(self, path):
        return self._exec(["cat", path])[1]

    def leaks(self, secret):
        if not self._started:
            return []  # no process ran in it, so nothing could have written a credential
        # The secret reaches grep through the exec environment; /proc would show it back.
        scan = ('grep -rlsF -e "$UAT_SECRET" --exclude-dir=proc --exclude-dir=sys --exclude-dir=dev / /dev/shm'
                ' || true')
        return self._exec(["sh", "-c", scan], {"UAT_SECRET": secret}, "/")[1].splitlines()

    def teardown(self):
        from docker.errors import NotFound

        if self._container._container is not None:
            with suppress(NotFound):
                self._container._container.remove(force=True, v=True)
            self._container._container, self._started = None, False
