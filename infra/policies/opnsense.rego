package whitelab.opnsense

# Stub. Implementation lands in PR3 alongside the OPNsense adapter.
# Invariants to encode:
#   - no `pass` rule with src=any dst=any (firewall/filter)
#   - 60_QUARANTINE retains DNS-redirect rules
#   - 40_ADMIN has no internet-egress rule
#   - SSH listen-iface is not '*'
#   - captiveportal EmergencyAccess exists with concurrentlogins=1

deny[msg] {
    false
    msg := "opnsense.rego stub"
}
