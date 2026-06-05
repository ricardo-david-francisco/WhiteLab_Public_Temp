package whitelab.lxc

# Stub. Implementation lands in PR6 (LXC golden-image promotion gate).
# Invariants:
#   - lineage in {"deb12-hardened-v1", "deb12-docker-v2"}
#   - audit_*.sh present in every ct-*/ directory
#   - bridge-vlan-aware true when any tag > 1 referenced

deny[msg] {
    false
    msg := "lxc.rego stub"
}
