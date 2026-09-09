FROM nixos/nix:2.35.2

ENV PATH=/opt/oat-tools/bin:/root/.nix-profile/bin:/bin:/usr/bin \
    HOME=/root \
    XDG_CONFIG_HOME=/root/.config \
    XDG_DATA_HOME=/root/.local/share \
    XDG_CACHE_HOME=/root/.cache \
    CI=1 \
    PAGER=cat \
    GIT_PAGER=cat \
    GH_PAGER=cat \
    GIT_TERMINAL_PROMPT=0 \
    GH_PROMPT_DISABLED=1 \
    TF_INPUT=0 \
    TF_IN_AUTOMATION=1 \
    AWS_EC2_METADATA_DISABLED=true

COPY sandbox/tools.nix /tmp/oat-tools.nix

# Build one deterministic environment instead of installing many packages into
# a mutable profile. The official Nix image already provides shell/core tools.
# Project-specific compilers and CLIs should come from the target repo's Nix/devenv.
RUN printf '%s\n' \
      'experimental-features = nix-command flakes' \
      'accept-flake-config = true' \
      'sandbox = false' \
      >> /etc/nix/nix.conf \
    && nix build --impure --out-link /opt/oat-tools --expr \
      'let flake = builtins.getFlake "nixpkgs"; pkgs = flake.legacyPackages.${builtins.currentSystem}; in import /tmp/oat-tools.nix { inherit pkgs; }' \
    && mkdir -p /root/.config/direnv /root/.local/share/direnv /root/.cache /workspace \
    && printf '%s\n' 'source /opt/oat-tools/share/nix-direnv/direnvrc' > /root/.config/direnv/direnvrc \
    && rm -f /tmp/oat-tools.nix

WORKDIR /workspace

# No host Docker daemon is exposed. Dockerfiles can be inspected; a project can
# supply linters/builders through Nix without receiving the host Docker socket.
CMD ["bash", "-lc", "trap : TERM INT; while sleep 3600; do :; done"]
