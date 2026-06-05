package whitelab.proxmox

# Stub. Implementation lands in PR4.
# Invariants:
#   - cluster firewall enabled (datacenter.cfg)
#   - ssh.socket masked on every node
#   - 2FA enrolled for the admin user
#   - no unprivileged=0 LXC outside explicit allow-list

deny[msg] {
    false
    msg := "proxmox.rego stub"
}
