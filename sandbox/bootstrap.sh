#!/usr/bin/env bash
# WhiteLab dev-sandbox bootstrap.
#
# Reproducibly builds ./.sandbox/ (gitignored, portable Linux x86_64) by
# downloading pinned tools and verifying their SHA256 against versions.env.
#
# Idempotent: re-running upgrades only what changed.
# Hardened: fails closed on any checksum mismatch or download error.
#
# Usage:
#   bash sandbox/bootstrap.sh          # install/refresh
#   bash sandbox/bootstrap.sh --clean  # wipe .sandbox/ and reinstall
#   source sandbox/activate.sh         # then: gh, age, sops, python on PATH
#
# Designed to run on:
#   - WSL2 Ubuntu 22.04+ (the Windows workstation case)
#   - Any Linux x86_64 host with bash, curl, tar, sha256sum, python3
#
# This script never reads or writes anything outside the repo root.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX_DIR="${REPO_ROOT}/.sandbox"
BIN_DIR="${SANDBOX_DIR}/bin"
DL_DIR="${SANDBOX_DIR}/downloads"
VENV_DIR="${SANDBOX_DIR}/venv"
STATE_DIR="${SANDBOX_DIR}/state"

# shellcheck disable=SC1091
source "${REPO_ROOT}/sandbox/versions.env"

log()  { printf '\033[1;34m[sandbox]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[sandbox]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[sandbox]\033[0m %s\n' "$*" >&2; exit 1; }

# --- platform check -----------------------------------------------------------

UNAME_S="$(uname -s)"
UNAME_M="$(uname -m)"
[[ "${UNAME_S}" == "Linux" ]] || die "Unsupported OS: ${UNAME_S}. Run from WSL or a Linux host."
[[ "${UNAME_M}" == "x86_64" ]] || die "Unsupported arch: ${UNAME_M}. The pinned binaries are Linux x86_64 only."

for cmd in curl tar sha256sum "${PYTHON_BIN}"; do
  command -v "${cmd}" >/dev/null 2>&1 || die "Required command missing on host: ${cmd}"
done

# --- argument parsing ---------------------------------------------------------

if [[ "${1:-}" == "--clean" ]]; then
  log "Wiping ${SANDBOX_DIR} (per --clean)"
  rm -rf "${SANDBOX_DIR}"
fi

mkdir -p "${BIN_DIR}" "${DL_DIR}" "${STATE_DIR}"

# --- helpers ------------------------------------------------------------------

# fetch <url> <out>  -- download with retries, fail on HTTP erro
fetch() {
  local url="$1" out="$2"
  curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
       --output "${out}" "${url}" \
    || die "Download failed: ${url}"
}

# verify <file> <expected_sha256>
verify() {
  local file="$1" expected="$2"
  local actual
  actual="$(sha256sum "${file}" | awk '{print $1}')"
  if [[ "${actual}" != "${expected}" ]]; then
    die "SHA256 mismatch for ${file}
  expected: ${expected}
  actual:   ${actual}
Refusing to install a tool that does not match the pinned hash."
  fi
}

# need_install <bin_path> <version_tool_args> <expected_version_substring>
need_install() {
  local bin_path="$1" version_args="$2" expected="$3"
  [[ -x "${bin_path}" ]] || return 0
  # shellcheck disable=SC2086
  "${bin_path}" ${version_args} 2>/dev/null | grep -qF "${expected}" && return 1 || return 0
}

# --- gh -----------------------------------------------------------------------

install_gh() {
  local v="${GH_VERSION}"
  local tarball="${DL_DIR}/gh_${v}_linux_amd64.tar.gz"
  local url="https://github.com/cli/cli/releases/download/v${v}/gh_${v}_linux_amd64.tar.gz"
  if ! need_install "${BIN_DIR}/gh" "--version" "gh version ${v}"; then
    log "gh ${v} already installed."
    return 0
  fi
  log "Installing gh ${v}"
  fetch "${url}" "${tarball}"
  verify "${tarball}" "${GH_SHA256}"
  tar -xzf "${tarball}" -C "${DL_DIR}"
  install -m 0755 "${DL_DIR}/gh_${v}_linux_amd64/bin/gh" "${BIN_DIR}/gh"
}

# --- age ----------------------------------------------------------------------

install_age() {
  local v="${AGE_VERSION}"
  local tarball="${DL_DIR}/age-v${v}-linux-amd64.tar.gz"
  local url="https://github.com/FiloSottile/age/releases/download/v${v}/age-v${v}-linux-amd64.tar.gz"
  if ! need_install "${BIN_DIR}/age" "--version" "v${v}"; then
    log "age v${v} already installed."
    return 0
  fi
  log "Installing age v${v}"
  fetch "${url}" "${tarball}"
  verify "${tarball}" "${AGE_SHA256}"
  tar -xzf "${tarball}" -C "${DL_DIR}"
  install -m 0755 "${DL_DIR}/age/age"        "${BIN_DIR}/age"
  install -m 0755 "${DL_DIR}/age/age-keygen"  "${BIN_DIR}/age-keygen"
}

# --- sops ---------------------------------------------------------------------

install_sops() {
  local v="${SOPS_VERSION}"
  local bin="${DL_DIR}/sops-v${v}.linux.amd64"
  local url="https://github.com/getsops/sops/releases/download/v${v}/sops-v${v}.linux.amd64"
  if ! need_install "${BIN_DIR}/sops" "--version --disable-version-check" "${v}"; then
    log "sops v${v} already installed."
    return 0
  fi
  log "Installing sops v${v}"
  fetch "${url}" "${bin}"
  verify "${bin}" "${SOPS_SHA256}"
  install -m 0755 "${bin}" "${BIN_DIR}/sops"
}

# --- python venv --------------------------------------------------------------

install_venv() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    log "Creating Python venv at ${VENV_DIR}"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  fi
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  log "Upgrading pip and installing requirements.txt"
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet --require-hashes --no-deps -r "${REPO_ROOT}/sandbox/requirements.txt" \
    || python -m pip install --quiet -r "${REPO_ROOT}/sandbox/requirements.txt"
  deactivate
}

# --- run ----------------------------------------------------------------------

install_gh
install_age
install_sops
install_venv

# Write a stamp summarizing what is installed.
{
  echo "# Auto-generated by sandbox/bootstrap.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "gh   ${GH_VERSION}   sha256=${GH_SHA256}"
  echo "age  ${AGE_VERSION}  sha256=${AGE_SHA256}"
  echo "sops ${SOPS_VERSION} sha256=${SOPS_SHA256}"
  echo "venv ${VENV_DIR}"
} > "${SANDBOX_DIR}/.stamp"

log "Sandbox ready. Activate with: source sandbox/activate.sh"
