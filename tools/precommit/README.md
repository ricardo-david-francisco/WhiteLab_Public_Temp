# Pre-commit hooks

Hooks installed via [`pre-commit`](https://pre-commit.com/):

* `detect-plaintext-secrets.sh` — runs `gitleaks detect --staged`.
* `verify-anonymization.py` — runs the anonymizer in `--verify` mode
  on `infra/`. Equivalent to the `anonymization-gate` CI job.

Install once::

    pip install pre-commit
    pre-commit install
