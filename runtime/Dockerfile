FROM node:22-bookworm-slim

ARG OPENCODE_V1_VERSION=latest
ARG OPENCODE_V2_VERSION=beta

ENV DEBIAN_FRONTEND=noninteractive \
    CI=1 \
    PAGER=cat \
    GIT_PAGER=cat \
    GH_PAGER=cat \
    TF_INPUT=0 \
    TF_IN_AUTOMATION=1 \
    AWS_EC2_METADATA_DISABLED=true \
    NIX_CONFIG="experimental-features = nix-command flakes\naccept-flake-config = true\nsandbox = false"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      direnv \
      file \
      git \
      gnupg \
      jq \
      less \
      nix-bin \
      openssh-client \
      procps \
      python3 \
      python3-pip \
      python3-venv \
      ripgrep \
      shellcheck \
      tini \
      tree \
      unzip \
      xz-utils \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && . /etc/os-release \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-buildx-plugin docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /nix/var/nix/profiles/per-user/root /nix/var/nix/gcroots/per-user/root /etc/nix \
    && printf '%s\n' \
      'experimental-features = nix-command flakes' \
      'accept-flake-config = true' \
      'sandbox = false' \
      > /etc/nix/nix.conf \
    && git config --system --add safe.directory '*'

# Keep the two CLIs side-by-side. V2 currently ships as @opencode/cli@beta
# and exposes the opencode2 binary; V1 exposes opencode.
RUN npm install -g \
      "opencode-ai@${OPENCODE_V1_VERSION}" \
      "@opencode/cli@${OPENCODE_V2_VERSION}" \
    && npm cache clean --force

WORKDIR /opt/oat

# The host may still contain an old, uncommitted package-lock.json from the
# pre-container workflow. Build only from the committed package.json so a stale
# host lock cannot break the image build.
COPY package.json ./
RUN npm install --ignore-scripts --no-audit --no-fund

COPY requirements.txt ./
RUN python3 -m venv /opt/oat/.venv \
    && /opt/oat/.venv/bin/pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

COPY . /opt/oat

ENV PATH="/opt/oat/.venv/bin:${PATH}" \
    HOME=/root \
    XDG_CONFIG_HOME=/root/.config \
    XDG_DATA_HOME=/root/.local/share \
    XDG_CACHE_HOME=/root/.cache \
    XDG_STATE_HOME=/root/.local/state

RUN chmod +x /opt/oat/runtime/entrypoint \
    && mkdir -p /root/.config /root/.local/share /root/.local/state /root/.cache

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/oat/runtime/entrypoint"]
CMD ["2"]
