# The container backend's image: Linux with node, git, uv, Python, pinned agent runtimes and dotbrain.
# The suite builds it (backends.container_image) from a context it assembles: this file, prepare.py,
# the recording `dotbrain` shim, and a dotbrain wheel built from the checkout under test.
FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git python3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /usr/local/bin/
RUN npm install --global opencode-ai@1.18.35 && npm cache clean --force
RUN npm install --global @earendil-works/pi-coding-agent@1.4.0 && npm cache clean --force
# Cursor's install script downloads each CLI build from a versioned URL; fetch that build directly and check it.
RUN curl -fsSL -o /tmp/cursor.tgz https://downloads.cursor.com/lab/2026.10.22-27dcf5f/linux/x64/agent-cli-package.tar.gz \
    && echo "85296944e4600a83c4b764f578d1502bf9c416db200d33a593e8f3ecabfdc294  /tmp/cursor.tgz" | sha256sum -c - \
    && mkdir /opt/cursor-agent && tar --strip-components=1 -xzf /tmp/cursor.tgz -C /opt/cursor-agent \
    && rm /tmp/cursor.tgz && ln -s /opt/cursor-agent/cursor-agent /usr/local/bin/agent

# The real CLI stays off PATH: adapters must find the shim, which logs each call and runs it.
COPY *.whl /tmp/wheel/
RUN UV_TOOL_DIR=/opt/dotbrain/tools UV_TOOL_BIN_DIR=/opt/dotbrain/bin UV_PYTHON_DOWNLOADS=never \
        uv tool install /tmp/wheel/*.whl \
    && rm -rf /tmp/wheel /root/.cache/uv
COPY dotbrain /usr/local/bin/dotbrain
COPY prepare.py /opt/uat/prepare.py
RUN chmod 755 /usr/local/bin/dotbrain && mkdir -p /work/checkout && touch /work/dotbrain-calls.log
