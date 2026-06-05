#!/usr/bin/env bash
# Portable, hermetic audit bootstrap for WhiteLab 2.0.
#
# Goal: a fresh Linux machine (e.g. a clean VMware guest) can clone this
# repo and run the exact same audit gates that CI runs, without polluting
# the host. Everything lands under ./.sandbox/ which is gitignored.
#
# What it installs (into .sandbox/):
#   * Trivy CLI       (binary release, no root)
#   * Snyk CLI        (binary release, no root)
#   * Python venv     (.sandbox/venv) with pytest + tools requirements
#
# What it runs (when called with `audit`):
#   * pytest -q tools/anonymizer
#   * tools/anonymizer/anonymize.py --verify infra/
#   * trivy fs --severity HIGH,CRITICAL --exit-code 0 .
#   * trivy config --severity HIGH,CRITICAL --exit-code 0 .
#   * snyk code test --severity-threshold=high  (if SNYK_TOKEN is set)
#   * snyk iac test  --severity-threshold=high infra/lxc infra/proxmox infra/caddy
#
# Usage:
#   tools/audit-bootstrap.sh install   # download tools into .sandbox/
#   tools/audit-bootstrap.sh audit     # run the full audit suite
#   tools/audit-bootstrap.sh           # install + audit
#
# Snyk auth (optional, only needed for snyk-* gates):
#   export SNYK_TOKEN=... ; tools/audit-bootstrap.sh audit

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SANDBOX="$ROOT/.sandbox"
BIN="$SANDBOX/bin"
VENV="$SANDBOX/venv"
mkdir -p "$BIN"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH=amd64 ;;
    aarch64|arm64) ARCH=arm64 ;;
    *) echo "unsupported arch: $ARCH" >&2; exit 2 ;;
esac

TRIVY_VERSION="${TRIVY_VERSION:-0.55.2}"

install_trivy() {
    if [ -x "$BIN/trivy" ]; then
        echo "trivy already installed: $($BIN/trivy --version | head -1)"
        return
    fi
    echo "installing trivy $TRIVY_VERSION ..."
    local tmp
    tmp="$(mktemp -d)"
    local url="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_${OS^}-${ARCH^^}.tar.gz"
    # Trivy release naming: Linux-64bit / macOS-64bit. Map ours.
    case "$OS-$ARCH" in
        linux-amd64) url="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" ;;
        linux-arm64) url="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-ARM64.tar.gz" ;;
        darwin-amd64) url="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_macOS-64bit.tar.gz" ;;
        darwin-arm64) url="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_macOS-ARM64.tar.gz" ;;
        *) echo "unsupported os/arch for trivy: $OS-$ARCH" >&2; exit 2 ;;
    esac
    curl -sSL "$url" -o "$tmp/trivy.tgz"
    tar -xzf "$tmp/trivy.tgz" -C "$tmp" trivy
    mv "$tmp/trivy" "$BIN/trivy"
    chmod +x "$BIN/trivy"
    rm -rf "$tmp"
    "$BIN/trivy" --version | head -1
}

install_snyk() {
    if [ -x "$BIN/snyk" ]; then
        echo "snyk already installed: $($BIN/snyk --version)"
        return
    fi
    echo "installing snyk CLI ..."
    local url
    case "$OS-$ARCH" in
        linux-amd64) url="https://downloads.snyk.io/cli/latest/snyk-linux" ;;
        linux-arm64) url="https://downloads.snyk.io/cli/latest/snyk-linux-arm64" ;;
        darwin-amd64) url="https://downloads.snyk.io/cli/latest/snyk-macos" ;;
        darwin-arm64) url="https://downloads.snyk.io/cli/latest/snyk-macos-arm64" ;;
        *) echo "unsupported os/arch for snyk: $OS-$ARCH" >&2; exit 2 ;;
    esac
    curl -sSL "$url" -o "$BIN/snyk"
    chmod +x "$BIN/snyk"
    "$BIN/snyk" --version
}

install_python() {
    if [ ! -d "$VENV" ]; then
        echo "creating python venv at $VENV ..."
        python3 -m venv "$VENV"
    fi
    # shellcheck disable=SC1091
    . "$VENV/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet pytest pyyaml
    if [ -f "$ROOT/tools/requirements.txt" ]; then
        pip install --quiet -r "$ROOT/tools/requirements.txt"
    fi
    deactivate
}

cmd_install() {
    install_trivy
    install_snyk
    install_python
    echo
    echo "Audit toolchain installed under $SANDBOX"
    echo "Add to PATH for this shell:  export PATH=\"$BIN:\$PATH\""
}

cmd_audit() {
    export PATH="$BIN:$PATH"
    # shellcheck disable=SC1091
    . "$VENV/bin/activate"

    local rc=0
    echo "=== pytest (anonymizer) ==="
    pytest -q tools/anonymizer || rc=$?

    echo
    echo "=== anonymizer verify ==="
    python3 tools/anonymizer/anonymize.py --verify infra/ || rc=$?

    echo
    echo "=== trivy fs ==="
    trivy fs --severity HIGH,CRITICAL --exit-code 0 --ignore-unfixed . || rc=$?

    echo
    echo "=== trivy config ==="
    trivy config --severity HIGH,CRITICAL --exit-code 0 . || rc=$?

    if [ -n "${SNYK_TOKEN:-}" ]; then
        echo
        echo "=== snyk code test ==="
        snyk code test --severity-threshold=high || true
        echo
        echo "=== snyk iac test ==="
        snyk iac test --severity-threshold=high infra/lxc/ infra/proxmox/ infra/caddy/ || true
    else
        echo
        echo "SNYK_TOKEN not set; skipping snyk-* gates."
        echo "  export SNYK_TOKEN=...  to enable."
    fi

    deactivate
    return "$rc"
}

case "${1:-all}" in
    install) cmd_install ;;
    audit)   cmd_audit ;;
    all)     cmd_install; cmd_audit ;;
    *) echo "usage: $0 [install|audit|all]" >&2; exit 64 ;;
esac
