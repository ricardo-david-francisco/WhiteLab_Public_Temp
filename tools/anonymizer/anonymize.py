"""WhiteLab anonymizer.

Deterministic scrub of secrets and identifying values from configuration
files. Outputs an anonymized file plus a JSON map (gitignored) that the
home-side Fortress Agent uses for rehydration. Idempotent: running on an
already-anonymized file produces no new mappings.

Usage::

    python -m tools.anonymizer.anonymize \\
        --in /tmp/cluster.fw \\
        --out infra/proxmox/n95/exports/cluster.fw.anonymized \\
        --format text

    python -m tools.anonymizer.anonymize --verify infra/

See docs/architecture/2.0-fortress-design.md sec.5 for the contract.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib
import ipaddress
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from tools.anonymizer.secret_map import (
    is_encrypted_map_path,
    load_encrypted_map,
    resolve_identity_key,
    save_encrypted_map,
)

# ---------------------------------------------------------------------------
# Map / lexicon
# ---------------------------------------------------------------------------

MAP_VERSION = 1
DEFAULT_MAP = Path(".anonmap.json")
DEFAULT_RULES = Path(__file__).parent / "rules.yaml"


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def load_map(path: Path) -> Dict[str, Any]:
    if is_encrypted_map_path(path):
        identity = resolve_identity_key()
        if identity is None:
            raise SystemExit(
                f"map {path}: no age identity available. Set "
                "$WHITELAB_ANONMAP_KEY or place vault/anonmap.key."
            )
        data = load_encrypted_map(path, identity)
    else:
        if not path.exists():
            return {"version": MAP_VERSION, "classes": {}}
        data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != MAP_VERSION:
        raise SystemExit(f"map {path}: unsupported version {data.get('version')!r}")
    return data


def save_map(path: Path, data: Dict[str, Any]) -> None:
    if is_encrypted_map_path(path):
        identity = resolve_identity_key()
        if identity is None:
            raise SystemExit(
                f"map {path}: no age identity available; cannot save "
                "encrypted map."
            )
        save_encrypted_map(path, data, identity)
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def allocate_placeholder(
    mp: Dict[str, Any], cls: str, value: str
) -> str:
    """Return placeholder for `value` in class `cls`. Allocate if new."""
    classes = mp.setdefault("classes", {})
    bucket: List[Dict[str, str]] = classes.setdefault(cls, [])
    for entry in bucket:
        if entry["value"] == value:
            return entry["id"]
    new_id = f"{cls}_{len(bucket) + 1:03d}"
    bucket.append({"id": new_id, "value": value, "first_seen": _utcnow()})
    return new_id


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

_PLACEHOLDER_MAC_RE = re.compile(r"^(?:[Xx]{2}|AA:BB:CC):", re.ASCII)


def not_placeholder_mac(s: str) -> bool:
    if s.upper().startswith(("XX:", "AA:BB:CC:")):
        return False
    if _PLACEHOLDER_MAC_RE.match(s):
        return False
    return True


def is_public_ipv4(s: str) -> bool:
    try:
        addr = ipaddress.IPv4Address(s)
    except ValueError:
        return False
    if not addr.is_global or addr.is_multicast:
        return False
    # Well-known public anycast DNS / NTP / time resolvers are not secrets.
    if s in _PUBLIC_ALLOWLIST_V4:
        return False
    return True


_PUBLIC_ALLOWLIST_V4 = frozenset({
    "1.1.1.1", "1.0.0.1",          # Cloudflare
    "8.8.8.8", "8.8.4.4",          # Google
    "9.9.9.9", "149.112.112.112",  # Quad9
    "208.67.222.222", "208.67.220.220",  # OpenDNS
    "192.0.2.0",                    # RFC5737 doc range starts
})


def is_public_ipv6(s: str) -> bool:
    try:
        addr = ipaddress.IPv6Address(s)
    except ValueError:
        return False
    return addr.is_global and not addr.is_multicast


def is_tailscale_tailnet(s: str) -> bool:
    # The capture group; rule_apply already strips the '.ts.net' suffix.
    if s in {"www", "login", "controlplane", "api", "pkgs", "tailscale"}:
        return False
    return True


_WG_KEY_BLACKLIST = {
    "EXAMPLE_WG_PRIVATE_KEY_AAAAAAAAAAAAAAAAAAAAAAA=",
}


def is_wireguard_private_key(s: str) -> bool:
    if s in _WG_KEY_BLACKLIST:
        return False
    return True


# Values that *look* like a secret pattern but are obviously not one
# (env-var references, well-known placeholders, the literal word
# "changeme" used in examples, etc.). Adding to this list is the only
# way to silence a PASSWORD/API_KEY/BEARER_TOKEN false-positive without
# disabling the rule.
_SECRET_OBVIOUS_NON_SECRETS = frozenset({
    "changeme", "redacted", "placeholder", "your-token-here",
    "your_token_here", "yourtokenhere", "example", "todo", "fixme",
    "true", "false", "null", "none",
})


def is_real_secret(s: str) -> bool:
    """Reject obvious non-secrets so PR review is not buried in noise."""
    low = s.lower()
    if low in _SECRET_OBVIOUS_NON_SECRETS:
        return False
    # Env-var reference like $VAR, ${VAR}, %VAR%, <VAR>.
    if s.startswith(("$", "${", "%", "<")) and s.endswith(("$", "}", "%", ">")):
        return False
    if s.startswith("$") or s.startswith("${"):
        return False
    # Already-redacted placeholders coming from this very pipeline.
    if _is_placeholder(s):
        return False
    return True


VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "not_placeholder_mac": not_placeholder_mac,
    "is_public_ipv4": is_public_ipv4,
    "is_public_ipv6": is_public_ipv6,
    "is_tailscale_tailnet": is_tailscale_tailnet,
    "is_wireguard_private_key": is_wireguard_private_key,
    "is_real_secret": is_real_secret,
}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class Rule:
    __slots__ = ("cls", "pattern", "validator", "capture", "keep")

    # Hard upper bound on the size of a regex pattern loaded from rules.yaml.
    # The rules file is committed and reviewed, so this is defence-in-depth
    # against a future malformed pattern accidentally enabling catastrophic
    # backtracking (CWE-1333 / Snyk ReDoS).
    _MAX_PATTERN_LEN = 1024

    def __init__(self, raw: Dict[str, Any]) -> None:
        self.cls: str = raw["class"]
        if "pattern" not in raw:
            self.pattern: Optional[re.Pattern[str]] = None
        else:
            pattern_src = raw["pattern"]
            if not isinstance(pattern_src, str):
                raise ValueError(
                    f"rule {self.cls!r}: pattern must be a string"
                )
            if len(pattern_src) > self._MAX_PATTERN_LEN:
                raise ValueError(
                    f"rule {self.cls!r}: pattern exceeds "
                    f"{self._MAX_PATTERN_LEN} chars"
                )
            self.pattern = re.compile(pattern_src)
        self.validator: Optional[Callable[[str], bool]] = (
            VALIDATORS.get(raw["validator"]) if raw.get("validator") else None
        )
        self.capture: int = int(raw.get("capture", 0))
        self.keep: bool = bool(raw.get("keep", False))


def load_rules(path: Path) -> Tuple[List[Rule], Dict[str, Dict[str, Any]]]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = [Rule(r) for r in cfg.get("regex_rules", []) if r.get("pattern")]
    hooks = {h["format"]: h for h in cfg.get("format_hooks", [])}
    return rules, hooks


# ---------------------------------------------------------------------------
# Scrub passes
# ---------------------------------------------------------------------------

def _is_placeholder(s: str) -> bool:
    """Identify already-anonymized tokens like MAC_001, PUBLIC_IPV4_042."""
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]+_[0-9]{3,}", s))


def scrub_text(text: str, rules: List[Rule], mp: Dict[str, Any]) -> str:
    """Apply regex rules left-to-right. Idempotent."""
    out = text
    for rule in rules:
        if rule.pattern is None or rule.keep:
            continue

        def _sub(match: re.Match[str], _rule: Rule = rule) -> str:
            captured = match.group(_rule.capture) if _rule.capture else match.group(0)
            if _is_placeholder(captured):
                return match.group(0)
            if _rule.validator is not None and not _rule.validator(captured):
                return match.group(0)
            placeholder = allocate_placeholder(mp, _rule.cls, captured)
            if _rule.capture:
                # Substitute only the captured group, preserve surrounding context.
                start, end = match.span(_rule.capture)
                full = match.group(0)
                rel_start = start - match.start(0)
                rel_end = end - match.start(0)
                return full[:rel_start] + placeholder + full[rel_end:]
            return placeholder

        out = rule.pattern.sub(_sub, out)
    return out


# ---------------------------------------------------------------------------
# Format dispatch
# ---------------------------------------------------------------------------

def dispatch_format(
    fmt: str,
    raw: bytes,
    rules: List[Rule],
    hooks: Dict[str, Dict[str, Any]],
    mp: Dict[str, Any],
) -> bytes:
    spec = hooks.get(fmt)
    if spec is None:
        raise SystemExit(f"unknown format: {fmt!r}")
    handler_path = spec.get("handler")
    if not handler_path:
        # Generic text mode — regex rules only.
        text = raw.decode("utf-8", errors="replace")
        return scrub_text(text, rules, mp).encode("utf-8")
    # Static dispatch table. Format hooks are imported lazily *by literal
    # name* — never by a string derived from configuration. This keeps the
    # import surface fully closed (CWE-94 / Snyk Code Injection): any handler
    # added in future must be wired here explicitly.
    handler = _STATIC_HOOKS.get(handler_path)
    if handler is None:
        raise SystemExit(
            f"format hook not implemented yet: {handler_path}. "
            f"Use --format text for a generic regex pass."
        )
    return handler(raw, rules=rules, mp=mp, scrub_text=scrub_text)


def _load_static_hooks() -> Dict[str, Callable[..., bytes]]:
    """Import known hook modules by literal name and build a closed dispatch.

    Hooks that are not yet implemented are simply absent from the result,
    which causes :func:`dispatch_format` to surface a clean error.
    """
    table: Dict[str, Callable[..., bytes]] = {}
    # Each entry below MUST use a literal module path; never interpolate.
    candidates: List[Tuple[str, str, str]] = [
        ("tools.anonymizer.format_hooks.opnsense", "scrub",
         "tools.anonymizer.format_hooks.opnsense:scrub"),
        ("tools.anonymizer.format_hooks.proxmox", "scrub_tfa",
         "tools.anonymizer.format_hooks.proxmox:scrub_tfa"),
        ("tools.anonymizer.format_hooks.proxmox", "scrub_clusterfw",
         "tools.anonymizer.format_hooks.proxmox:scrub_clusterfw"),
        ("tools.anonymizer.format_hooks.omada", "scrub_backup",
         "tools.anonymizer.format_hooks.omada:scrub_backup"),
        ("tools.anonymizer.format_hooks.caddy", "scrub_logs",
         "tools.anonymizer.format_hooks.caddy:scrub_logs"),
    ]
    for mod_name, attr, key in candidates:
        try:
            # Literal arguments only — Snyk Code Injection sink is unreachable.
            mod = importlib.import_module(mod_name)  # noqa: S412
        except ModuleNotFoundError:
            continue
        fn = getattr(mod, attr, None)
        if callable(fn):
            table[key] = fn
    return table


_STATIC_HOOKS: Dict[str, Callable[..., bytes]] = _load_static_hooks()


# ---------------------------------------------------------------------------
# Verify mode
# ---------------------------------------------------------------------------

def verify_tree(root: Path, rules: List[Rule]) -> int:
    """Walk a tree and fail if any committed file contains a real secret."""
    ignored_suffixes = {".gitkeep", ".png", ".jpg", ".pdf"}
    failures: List[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in ignored_suffixes:
            continue
        if any(part in {".git", ".sandbox", "node_modules"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for rule in rules:
            if rule.pattern is None or rule.keep:
                continue
            for match in rule.pattern.finditer(text):
                value = match.group(rule.capture) if rule.capture else match.group(0)
                if _is_placeholder(value):
                    continue
                if rule.validator is not None and not rule.validator(value):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path}:{line}: cleartext {rule.cls}: {value[:24]}...")
    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        print(f"\nverify FAILED: {len(failures)} cleartext hit(s).", file=sys.stderr)
        return 1
    print("verify OK.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="anonymize", description=__doc__)
    p.add_argument("--in", dest="src", type=Path, help="input file")
    p.add_argument("--out", dest="dst", type=Path, help="output file")
    p.add_argument(
        "--format",
        default="text",
        help="text | opnsense_xml | proxmox_tfacfg | proxmox_clusterfw | omada_db | caddy",
    )
    p.add_argument("--map-file", dest="map_file", type=Path, default=DEFAULT_MAP)
    p.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    p.add_argument(
        "--verify",
        type=Path,
        nargs="?",
        const=Path("."),
        default=None,
        help="verify a tree contains no cleartext secrets and exit",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rules, hooks = load_rules(args.rules)

    if args.verify is not None:
        return verify_tree(args.verify, rules)

    if not args.src or not args.dst:
        print("error: --in and --out are required (or use --verify)", file=sys.stderr)
        return 2

    mp = load_map(args.map_file)
    raw = args.src.read_bytes()
    out = dispatch_format(args.format, raw, rules, hooks, mp)
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    args.dst.write_bytes(out)
    save_map(args.map_file, mp)
    print(
        f"anonymized {args.src} -> {args.dst} "
        f"({sum(len(v) for v in mp.get('classes', {}).values())} mappings)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
