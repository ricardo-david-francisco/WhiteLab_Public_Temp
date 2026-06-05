# policy/zero_trust.rego
#
# Zero-trust invariants for declarative manifests. Evaluated by
# the anonymization-gate / future OPA-conftest step. The policy is
# deliberately narrow: it forbids *re-introduction* of three
# specific shapes that violate ADR-0002 and the deep-dive zero-trust
# posture.

package whitelab.zero_trust

# 1. No service may declare an inbound listener on TCP port 22.
deny[msg] {
  input.services[svc].ports[_].port == 22
  input.services[svc].ports[_].protocol == "tcp"
  msg := sprintf(
    "service '%s' declares an inbound TCP/22 listener; SSH is forbidden (ADR-0002).",
    [svc],
  )
}

# 2. No systemd unit named "ssh.service" or "sshd.service" may be
#    declared "enabled".
deny[msg] {
  unit := input.systemd_units[_]
  unit.enabled == true
  ssh_unit_names[unit.name]
  msg := sprintf(
    "systemd unit '%s' is enabled; SSH must remain masked (ADR-0002).",
    [unit.name],
  )
}

ssh_unit_names := {"ssh.service", "sshd.service", "ssh.socket", "sshd.socket"}

# 3. Default-allow east-west firewall rules are forbidden. Every
#    rule must declare an explicit source set; "any -> any" is
#    rejected.
deny[msg] {
  rule := input.firewall.rules[_]
  rule.action == "allow"
  rule.source == "any"
  rule.destination == "any"
  msg := sprintf(
    "firewall rule '%s' allows any -> any; default-allow is forbidden.",
    [rule.name],
  )
}
