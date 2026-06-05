# Containerized variant of the WhiteLab dev sandbox.
#
# Use this when:
#   - You want maximum isolation from the host.
#   - You are on a host without WSL but with Docker.
#   - You want to bake the sandbox into a CI image later.
#
# The bare-metal flow (sandbox/bootstrap.sh + .sandbox/) remains the default
# for local interactive work because it preserves browser-based gh auth.
#
# Build and use:
#   docker compose -f sandbox/docker-compose.yml run --rm sandbox

# Pinned by digest in CI; floating tag here for first-run convenience.
FROM debian:13-slim

ARG GH_VERSION=2.92.0
ARG GH_SHA256=b57848131bdf0c229cd35e1f2a51aa718199858b2e728410b37e89a428943ec4
ARG AGE_VERSION=1.2.1
ARG AGE_SHA256=7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50
ARG SOPS_VERSION=3.9.4
ARG SOPS_SHA256=5488e32bc471de7982ad895dd054bbab3ab91c417a118426134551e9626e4e85

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# System baseline. Versions are pinned by Debian's stable suite, not by us.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq python3 python3-venv python3-pip \
        tar gnupg openssh-client unzip \
 && rm -rf /var/lib/apt/lists/*

# gh
RUN curl -fLSso /tmp/gh.tgz \
        "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" \
 && echo "${GH_SHA256}  /tmp/gh.tgz" | sha256sum -c - \
 && tar -xzf /tmp/gh.tgz -C /tmp \
 && install -m 0755 "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" /usr/local/bin/gh \
 && rm -rf /tmp/gh*

# age
RUN curl -fLSso /tmp/age.tgz \
        "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz" \
 && echo "${AGE_SHA256}  /tmp/age.tgz" | sha256sum -c - \
 && tar -xzf /tmp/age.tgz -C /tmp \
 && install -m 0755 /tmp/age/age        /usr/local/bin/age \
 && install -m 0755 /tmp/age/age-keygen /usr/local/bin/age-keygen \
 && rm -rf /tmp/age*

# sops
RUN curl -fLSso /usr/local/bin/sops \
        "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64" \
 && echo "${SOPS_SHA256}  /usr/local/bin/sops" | sha256sum -c - \
 && chmod 0755 /usr/local/bin/sops

# Non-root user. UID 1000 matches typical WSL/Linux desktop accounts so files
# created in the bind-mounted repo inherit the right ownership.
RUN useradd --create-home --shell /bin/bash --uid 1000 whitelab
USER whitelab
WORKDIR /workspace

COPY --chown=whitelab:whitelab requirements.txt /tmp/requirements.txt
RUN python3 -m venv /home/whitelab/.venv \
 && /home/whitelab/.venv/bin/pip install --upgrade pip \
 && /home/whitelab/.venv/bin/pip install -r /tmp/requirements.txt
ENV PATH="/home/whitelab/.venv/bin:${PATH}"

CMD ["bash", "-l"]
