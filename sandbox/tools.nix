{ pkgs }:

pkgs.buildEnv {
  name = "opencode-agent-toolkit-tools";
  paths = with pkgs; [
    git
    direnv
    nix-direnv
    python3
    jq
    yq-go
    ripgrep
    fd
    tree
    file
    just
    shellcheck
    actionlint
  ];
  pathsToLink = [ "/bin" "/share/nix-direnv" ];
}
