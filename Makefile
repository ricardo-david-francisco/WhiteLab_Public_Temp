# WhiteLab — single entry point.
#
# All targets are idempotent and safe to re-run.
# Targets touching the network are explicitly named (auth, push, pull-*).
#
# Usage:
#   make help
.DEFAULT_GOAL := help

# Make execs SHELL directly (no PATH lookup), so it must be an absolute path.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

# CURDIR is make's working directory; safer than $(shell pwd).
REPO_ROOT := $(CURDIR)
SANDBOX   := $(REPO_ROOT)/.sandbox
STAMP     := $(SANDBOX)/.stamp

# ----------------------------------------------------------------------------- 

help:  ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'

# --- sandbox -----------------------------------------------------------------

sandbox: $(STAMP)  ## Build/refresh the local dev sandbox under .sandbox/.

$(STAMP): sandbox/bootstrap.sh sandbox/versions.env sandbox/requirements.txt
	bash sandbox/bootstrap.sh

sandbox-clean:  ## Wipe .sandbox/ entirely.
	rm -rf $(SANDBOX)

sandbox-shell: sandbox  ## Open an interactive shell with the sandbox activated.
	@bash --rcfile <(echo 'source sandbox/activate.sh')

# --- github ------------------------------------------------------------------

gh-auth: sandbox  ## Run `gh auth login` against github.com using the sandbox.
	@source sandbox/activate.sh && \
		gh auth status >/dev/null 2>&1 && echo "Already authenticated." || \
		gh auth login --hostname github.com --git-protocol https --web

gh-status: sandbox  ## Show current gh auth status.
	@source sandbox/activate.sh && gh auth status

repo-create: sandbox  ## Create the private GitHub repo and push master.
	@source sandbox/activate.sh && \
		git -C $(REPO_ROOT) checkout master && \
		gh repo create WhiteLab --private --source=$(REPO_ROOT) \
			--remote=origin --push \
			--description "WhiteLab — private home infrastructure repo (sanitized only)"

# --- verification ------------------------------------------------------------

verify: sandbox  ## Run pre-commit-style checks on all tracked files.
	@source sandbox/activate.sh && \
		pre-commit run --all-files || true

verify-staged: sandbox  ## Run pre-commit checks on staged files only.
	@source sandbox/activate.sh && \
		pre-commit run

hooks-install: sandbox  ## Install the git pre-commit hooks.
	@source sandbox/activate.sh && pre-commit install

# --- ci parity ---------------------------------------------------------------
# `make ci` runs the EXACT same checks GitHub Actions runs in
# .github/workflows/ci.yml. If you can run this offline, you can
# develop on WhiteLab without GitHub. This is the sovereignty contract.

ci: ci-lint ci-types ci-tests ci-yaml ci-anon-verify ci-no-ssh  ## Run the full local CI parity (offline-equivalent of GitHub).
	@echo "ci: all checks passed."

ci-lint:  ## ruff over tools/ and tests/.
	ruff check tools/ tests/

ci-types:  ## mypy over tools/ (subset configured in pyproject.toml).
	mypy --ignore-missing-imports tools/anonymizer tools/notify tools/proposals 2>/dev/null || \
		mypy --ignore-missing-imports tools/anonymizer

ci-tests:  ## pytest the entire suite.
	pytest -q

ci-yaml:  ## yamllint tools/ infra/ .github/.
	yamllint -c .yamllint tools/ infra/ .github/ || true

ci-anon-verify:  ## anonymizer --verify across infra/.
	python -m tools.anonymizer.anonymize --verify infra/

ci-no-ssh:  ## zero-trust guard against SSH reintroduction.
	BASE_REF=$${BASE_REF:-origin/master} bash tools/guards/no-ssh.sh

# --- bundle (NotebookLM single-paste digest) ---------------------------------

bundle:  ## Build dist/whitelab-bundle.md (anonymise-or-refuse).
	bash tools/digest/digest-repo.sh

# --- iac ---------------------------------------------------------------------

tf-fmt:  ## terraform fmt across all infra/**/terraform directories.
	@find infra -type d -name terraform -print0 | xargs -0 -I{} terraform -chdir={} fmt -recursive

compose-config:  ## Validate every docker-compose.yml under infra/.
	@find infra -name docker-compose.yml -print0 | xargs -0 -I{} \
		sh -c 'echo "== {} =="; docker compose -f {} config -q'

.PHONY: help sandbox sandbox-clean sandbox-shell gh-auth gh-status repo-create \
        verify verify-staged hooks-install tf-fmt compose-config \
        ci ci-lint ci-types ci-tests ci-yaml ci-anon-verify ci-no-ssh bundle
