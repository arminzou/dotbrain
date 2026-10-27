# The container backend's image: Linux with node, git, uv, Python, the six pinned agent runtimes
# (Claude Code, Codex, OpenCode, Pi, Cursor, Hermes; see evidence.py) and dotbrain.
# The suite builds it (backends.container_image) from a context it assembles: this file, prepare.py,
# the recording `dotbrain` shim, and a dotbrain wheel built from the checkout under test.
#
# A runtime whose install fails does not fail the build: the failure's output goes to
# /opt/uat/skip/<runtime>, and that runtime's journeys skip with it as the reason.
FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git python3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/uat/skip
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /usr/local/bin/
RUN (npm install --global @anthropic-ai/claude-code@2.1.311 && npm cache clean --force) >/tmp/i.log 2>&1 \
    || tail -c 600 /tmp/i.log >/opt/uat/skip/claude
RUN (npm install --global @openai/codex@0.164.0 && npm cache clean --force) >/tmp/i.log 2>&1 \
    || tail -c 600 /tmp/i.log >/opt/uat/skip/codex
RUN (npm install --global opencode-ai@1.18.35 && npm cache clean --force) >/tmp/i.log 2>&1 \
    || tail -c 600 /tmp/i.log >/opt/uat/skip/opencode
RUN (npm install --global @earendil-works/pi-coding-agent@1.4.0 && npm cache clean --force) >/tmp/i.log 2>&1 \
    || tail -c 600 /tmp/i.log >/opt/uat/skip/pi
# Cursor's install script downloads each CLI build from a versioned URL; fetch that build directly and check it.
RUN (curl -fsSL -o /tmp/cursor.tgz https://downloads.cursor.com/lab/2026.10.22-27dcf5f/linux/x64/agent-cli-package.tar.gz \
    && echo "85296944e4600a83c4b764f578d1502bf9c416db200d33a593e8f3ecabfdc294  /tmp/cursor.tgz" | sha256sum -c - \
    && mkdir /opt/cursor-agent && tar --strip-components=1 -xzf /tmp/cursor.tgz -C /opt/cursor-agent \
    && rm /tmp/cursor.tgz && ln -s /opt/cursor-agent/cursor-agent /usr/local/bin/agent) >/tmp/i.log 2>&1 \
    || tail -c 600 /tmp/i.log >/opt/uat/skip/cursor

# Hermes has no package-registry release: its installer clones the repo, so pin the release commit (v0.22.0+119)
# and the installer script's checksum. Accepted gap: the installer's own uv, Python and dependency downloads float.
RUN (curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/hermes-install.sh \
    && echo "abf338605dae6dd28d101673ac6aed7995c955745db46d47676bc591a7957209  /tmp/hermes-install.sh" | sha256sum -c - \
    && bash /tmp/hermes-install.sh --commit 0e427d788d253630d38a3a51cd76849e73cd6925 \
        --dir /opt/hermes --non-interactive --skip-browser --skip-computer-use \
    && rm /tmp/hermes-install.sh && ln -s /root/.local/bin/hermes /usr/local/bin/hermes) >/tmp/i.log 2>&1 \
    || tail -c 600 /tmp/i.log >/opt/uat/skip/hermes

# The real CLI stays off PATH: adapters must find the shim, which logs each call and runs it.
COPY *.whl /tmp/wheel/
RUN UV_TOOL_DIR=/opt/dotbrain/tools UV_TOOL_BIN_DIR=/opt/dotbrain/bin UV_PYTHON_DOWNLOADS=never \
        uv tool install /tmp/wheel/*.whl \
    && rm -rf /tmp/wheel /root/.cache/uv
COPY dotbrain /usr/local/bin/dotbrain
COPY prepare.py /opt/uat/prepare.py
RUN chmod 755 /usr/local/bin/dotbrain && mkdir -p /work/checkout && touch /work/dotbrain-calls.log
