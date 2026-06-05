#!/usr/bin/env bash
# Audit script for CT-105 (AdGuard Home DMZ resolver).
# Mirrors the four-section bible audit pattern:
#   1. Network identity
#   2. Security baseline
#   3. Application layer (AdGuard control + DNS)
#   4. Reverse-proxy reachability
set -euo pipefail

CT=105
NODE=n305
DMZ_IP=192.168.25.10

section() { printf "\n=== %s ===\n" "$1"; }

section "1. Network identity"
ip -br addr show | grep -E "(eth0|net0)" || true
ip route get 1.1.1.1 || true
ss -lntu | grep -E ":(53|3000)\b" || true

section "2. Security baseline"
test -f /etc/ssh/sshd_config && grep -E "^(PermitRootLogin|PasswordAuthentication)" /etc/ssh/sshd_config || true
systemctl is-enabled --quiet ufw && ufw status verbose || echo "UFW not active (expected on docker-v2)"
docker info --format '{{.SecurityOptions}}' 2>/dev/null || true

section "3. Application layer — AdGuard"
curl -fsS http://127.0.0.1:3000/control/status | head -c 300 ; echo
dig +short @${DMZ_IP} -p 53 example.com || true

section "4. Reverse-proxy reachability"
curl -fsSI -k "https://adguard.<TAILNET>.ts.net" -o /dev/null \
  && echo "Caddy reachable" \
  || echo "Caddy NOT reachable from this CT (expected — DMZ is one-way)"

echo "audit_ct${CT} complete"
