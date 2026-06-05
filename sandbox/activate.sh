# Source this file to put the sandbox tools on PATH for the current shell.
#   source sandbox/activate.sh
#
# Reversible: run `whitelab_deactivate` to restore the previous PATH.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "activate.sh must be sourced, not executed:  source sandbox/activate.sh" >&2
  exit 1
fi

_WHITELAB_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
_WHITELAB_SANDBOX="${_WHITELAB_REPO_ROOT}/.sandbox"

if [[ ! -d "${_WHITELAB_SANDBOX}/bin" ]]; then
  echo "[sandbox] .sandbox/ not found. Run: bash sandbox/bootstrap.sh" >&2
  return 1
fi

# Save original env so we can restore it.
export _WHITELAB_OLD_PATH="${PATH}"
export _WHITELAB_OLD_PS1="${PS1:-}"
export _WHITELAB_OLD_GH_CONFIG_DIR="${GH_CONFIG_DIR:-}"

# gh stores its config (token, hosts.yml) under GH_CONFIG_DIR. Pin it inside
# the sandbox so authentication state travels with the folder when copied to
# another machine. NEVER commit .sandbox/ — see .gitignore.
export GH_CONFIG_DIR="${_WHITELAB_SANDBOX}/state/gh"
mkdir -p "${GH_CONFIG_DIR}"

# Activate the python venv (if present) and prepend sandbox/bin.
if [[ -f "${_WHITELAB_SANDBOX}/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${_WHITELAB_SANDBOX}/venv/bin/activate"
fi
export PATH="${_WHITELAB_SANDBOX}/bin:${PATH}"

# Visible prompt marker.
PS1="(whitelab) ${PS1:-\$ }"

whitelab_deactivate() {
  if command -v deactivate >/dev/null 2>&1; then deactivate || true; fi
  export PATH="${_WHITELAB_OLD_PATH}"
  export PS1="${_WHITELAB_OLD_PS1}"
  if [[ -n "${_WHITELAB_OLD_GH_CONFIG_DIR}" ]]; then
    export GH_CONFIG_DIR="${_WHITELAB_OLD_GH_CONFIG_DIR}"
  else
    unset GH_CONFIG_DIR
  fi
  unset _WHITELAB_OLD_PATH _WHITELAB_OLD_PS1 _WHITELAB_OLD_GH_CONFIG_DIR
  unset _WHITELAB_REPO_ROOT _WHITELAB_SANDBOX
  unset -f whitelab_deactivate
}

echo "[sandbox] Activated. Tools on PATH: gh, age, sops, terraform, python (venv)."
echo "[sandbox] gh config dir pinned to: ${GH_CONFIG_DIR}"
echo "[sandbox] Deactivate with: whitelab_deactivate"
