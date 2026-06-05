#!/usr/bin/env bash
# Detect plaintext secrets staged for commit using gitleaks.
# Exits non-zero if any secret is detected.
set -euo pipefail

if ! command -v gitleaks >/dev/null 2>&1; then
    echo "gitleaks not installed; install via 'go install github.com/gitleaks/gitleaks/v8@latest' or download from releases."
    exit 1
fi

gitleaks detect --staged --no-banner --redact --exit-code 1
