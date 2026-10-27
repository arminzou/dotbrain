"""The container backend: a disposable Linux container from the UAT image, and a way to run commands in it.

Journeys use only ``run``, ``read``, ``put_dir`` and the sandbox paths as the container sees them.
"""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager, suppress
from pathlib import Path

HERE = Path(__file__).resolve().parent


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


def container_image(repo: Path, uv: str, lock_dir: Path) -> tuple[str, str]:
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
                           check=True, capture_output=True)
            shutil.copy(dockerfile, context)
            shutil.copy(HERE / "prepare.py", context)
            image = DockerImage(context, tag=tag, clean_up=False).build()
            return tag, image.get_wrapped_image().id


class ContainerBackend:
    """A container from the UAT image: its whole filesystem is the sandbox, and teardown removes it."""

    data_root = "/root/dotbrain"
    checkout = "/work/checkout"
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

    def start(self):
        try:
            self._container.start()
        except BaseException:
            with suppress(Exception):  # the caller's teardown retries and reports a failed removal
                self.teardown()
            raise

    def _exec(self, argv, env=None, cwd=None):
        code, (out, err) = self._container.get_wrapped_container().exec_run(
            argv, environment=env or None, workdir=cwd or self.checkout, demux=True)
        return code, (out or b"").decode("utf-8", "replace"), (err or b"").decode("utf-8", "replace")

    def run(self, argv, *, env=None, cwd=None, timeout=600):
        # OpenCode exits before a pipe drains and loses all output past 64 KiB, so the command writes
        # to in-memory files (/dev/shm) instead, unlinked before it starts.
        # `timeout` signals the command's whole process group; the container's removal ends the rest.
        script = ('o=$(mktemp -p /dev/shm) e=$(mktemp -p /dev/shm); exec 3>"$o" 4<"$o" 5>"$e" 6<"$e"; '
                  'rm -f "$o" "$e"; timeout -k 5 "$0" "$@" >&3 2>&5; code=$?; cat <&4; cat <&6 >&2; exit $code')
        code, out, err = self._exec(["sh", "-c", script, str(math.ceil(timeout)), *argv], env, cwd)
        if code in (124, 137):
            raise AssertionError(f"{argv[0]} ran past {timeout} s\n{out[-4000:]}\n{err[-4000:]}")
        return subprocess.CompletedProcess(argv, code, out, err)

    def read(self, path):
        return self._exec(["cat", path])[1]

    def put_dir(self, source: Path, folders, dest: str) -> None:
        """Copy ``folders`` of ``source`` into the container at ``dest`` (no ``__pycache__``)."""
        import io
        import tarfile

        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as tar:
            for name in folders:
                tar.add(source / name, arcname=name, filter=lambda info: None if "__pycache__" in info.name else info)
        self.run(["mkdir", "-p", dest])
        self._container.get_wrapped_container().put_archive(dest, data.getvalue())

    def unavailable(self, runtime: str, binary: str) -> str | None:
        """Why a runtime's journeys cannot run in this image, or ``None``: its recorded install failure
        or a missing binary. A failed plugin install is a product failure, not a skip: see ``install_plugin``."""
        if reason := self.read(f"/opt/uat/skip/{runtime}").strip():
            return f"{runtime} install failed in the image: {reason}"
        if self.run(["which", binary]).returncode:
            return f"{runtime}: `{binary}` is not in the image"
        return None

    def install_plugin(self, steps) -> None:
        """Run the plugin install ``steps`` in the checkout; the plugin is the checkout's own, so a failure fails."""
        for argv in steps:
            done = self.run(list(argv), cwd=self.checkout, timeout=300)
            assert done.returncode == 0, f"{' '.join(argv)} -> {done.returncode}\n{done.stdout}\n{done.stderr}"

    def version(self, binary: str) -> str:
        done = self.run([binary, "--version"])
        assert done.returncode == 0, f"{binary} --version -> {done.returncode}\n{done.stdout}\n{done.stderr}"
        return (done.stdout.strip() or done.stderr.strip()).splitlines()[0]

    def teardown(self):
        from docker.errors import NotFound

        if self._container._container is not None:
            with suppress(NotFound):
                self._container._container.remove(force=True, v=True)
            self._container._container = None
