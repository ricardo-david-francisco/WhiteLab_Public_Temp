package whitelab.secrets

# Forbid anything in infra/ that looks like a real cleartext secret.
# This is a stub. The Python --verify pass is the authoritative check;
# this Rego runs as belt-and-suspenders.

deny[msg] {
    input.kind == "file"
    re_match("-----BEGIN (?:OPENSSH|RSA|EC )?PRIVATE KEY-----", input.contents)
    msg := sprintf("cleartext private key in %s", [input.path])
}

deny[msg] {
    input.kind == "file"
    re_match("AGE-SECRET-KEY-1[A-Z0-9]{58}", input.contents)
    msg := sprintf("cleartext age secret in %s", [input.path])
}
