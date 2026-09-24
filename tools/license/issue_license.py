"""Founder-only license issuer — NOT shipped to customers, NOT a Django command.

One-time setup (on the founder's own machine, never on a server):

    python tools/license/issue_license.py --new-keypair --out D:/secure/conductor-license.pem

prints the PUBLIC key to paste into ``erp/licensing/keys.py``. Keep the .pem backed up offline:
losing it means no more renewals can be issued. If ``CONDUCTOR_LICENSE_KEY_PASSPHRASE`` is set the
.pem is encrypted with it (recommended).

Issue a key (after payment):

    set CONDUCTOR_LICENSE_PRIVATE_KEY=D:/secure/conductor-license.pem
    python tools/license/issue_license.py --company "شركة النيل للتجارة" --tax-id 123-456-789 \\
        --edition integrated --ai-years 1

Renewal = the same command with the SAME ``--license-id`` (printed on first issue) and a new
``--issued-at``/``--years``. Writes ``<tax-id>.lic`` (gitignored) and prints the key.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from erp.licensing.core import (  # noqa: E402  (Django-free by design)
    EDITIONS,
    LICENSABLE_MODULES,
    LicenseInfo,
    public_key_to_b64,
    sign,
    verify_with,
)

PRIVATE_KEY_ENV = "CONDUCTOR_LICENSE_PRIVATE_KEY"
PASSPHRASE_ENV = "CONDUCTOR_LICENSE_KEY_PASSPHRASE"


def _inside_repo(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == REPO_ROOT or REPO_ROOT in resolved.parents


def _passphrase() -> bytes | None:
    value = os.environ.get(PASSPHRASE_ENV)
    return value.encode("utf-8") if value else None


def add_years(day: dt.date, years: int) -> dt.date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 Feb -> 28 Feb in a non-leap year
        return day.replace(year=day.year + years, day=28)


def new_keypair(out: Path) -> str:
    if _inside_repo(out):
        raise SystemExit(f"Refusing: {out} is inside the repository. Keep the private key outside it.")
    if out.exists():
        raise SystemExit(f"Refusing: {out} already exists — never overwrite a signing key.")
    private_key = Ed25519PrivateKey.generate()
    passphrase = _passphrase()
    encryption = (serialization.BestAvailableEncryption(passphrase) if passphrase
                  else serialization.NoEncryption())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, encryption))
    return public_key_to_b64(private_key.public_key())


def load_private_key(path: Path) -> Ed25519PrivateKey:
    if _inside_repo(path):
        raise SystemExit(f"Refusing: {path} is inside the repository. Move the private key out.")
    key = serialization.load_pem_private_key(path.read_bytes(), password=_passphrase())
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit(f"{path} is not an Ed25519 private key.")
    return key


def build_info(args: argparse.Namespace) -> LicenseInfo:
    edition = EDITIONS[args.edition]
    modules = tuple(m.strip() for m in args.modules.split(",")) if args.modules else edition["modules"]
    unknown = sorted(set(modules) - set(LICENSABLE_MODULES))
    if unknown:
        raise SystemExit(f"Unknown modules: {unknown}. Known: {', '.join(LICENSABLE_MODULES)}")
    issued_at = dt.date.fromisoformat(args.issued_at) if args.issued_at else dt.date.today()
    if args.ai_until:
        ai_until = dt.date.fromisoformat(args.ai_until)
    elif args.ai_years:
        ai_until = add_years(issued_at, args.ai_years)
    else:
        ai_until = None
    if args.unlimited_branches:
        max_branches = None
    elif args.max_branches is not None:
        max_branches = args.max_branches
    else:
        max_branches = edition["max_branches"]
    return LicenseInfo(
        license_id=args.license_id or f"LIC-{uuid.uuid4().hex[:12].upper()}",
        company_name=args.company,
        tax_id=args.tax_id,
        edition=args.edition,
        modules=tuple(m for m in LICENSABLE_MODULES if m in modules),
        max_branches=max_branches,
        issued_at=issued_at,
        maintenance_until=add_years(issued_at, args.years),
        ai_until=ai_until,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Issue a Conductor perpetual license key (founder only).")
    p.add_argument("--new-keypair", action="store_true", help="Generate the signing keypair once.")
    p.add_argument("--out", type=Path, help="With --new-keypair: where to write the private .pem.")
    p.add_argument("--private-key", type=Path, help=f"Signing .pem (default: ${PRIVATE_KEY_ENV}).")
    p.add_argument("--company", help="Company name as it should appear (Arabic is fine).")
    p.add_argument("--tax-id", help="Company tax registration number the license binds to.")
    p.add_argument("--edition", choices=sorted(EDITIONS), default="basic")
    p.add_argument("--modules", help="Comma list overriding the edition's modules.")
    p.add_argument("--max-branches", type=int, help="Override the edition's branch allowance.")
    p.add_argument("--unlimited-branches", action="store_true")
    p.add_argument("--years", type=int, default=1, help="Maintenance years from issue date (default 1).")
    p.add_argument("--issued-at", help="ISO date (default today) — renewals set the renewal date.")
    p.add_argument("--ai-until", help="AI add-on end date (ISO).")
    p.add_argument("--ai-years", type=int, help="AI add-on length in years from issue date.")
    p.add_argument("--license-id", help="Reuse on renewal; generated on first issue.")
    p.add_argument("--out-dir", type=Path, default=Path.cwd(), help="Where to write <tax-id>.lic.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.new_keypair:
        if not args.out:
            raise SystemExit("--new-keypair needs --out <path outside the repo>")
        public = new_keypair(args.out)
        print(f"Private key written to {args.out} — back it up offline, never commit it.")
        if not _passphrase():
            print(f"WARNING: not encrypted. Set {PASSPHRASE_ENV} before generating to encrypt it.")
        print("Paste this PUBLIC key into erp/licensing/keys.py PUBLIC_KEYS:")
        print(public)
        return 0

    if not args.company or not args.tax_id:
        raise SystemExit("--company and --tax-id are required to issue a key")
    key_path = args.private_key or (Path(os.environ[PRIVATE_KEY_ENV]) if os.environ.get(PRIVATE_KEY_ENV) else None)
    if key_path is None:
        raise SystemExit(f"Set ${PRIVATE_KEY_ENV} or pass --private-key")
    private_key = load_private_key(key_path)
    info = build_info(args)
    key = sign(info, private_key)
    verify_with(key, [private_key.public_key()])  # self-check: never hand out a key that won't verify

    safe_name = "".join(c for c in info.tax_id if c.isalnum() or c in "-_") or "license"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    lic_path = args.out_dir / f"{safe_name}.lic"
    lic_path.write_text(key + "\n", encoding="utf-8")
    print(f"license_id: {info.license_id}  (reuse it on renewal)")
    print(f"edition: {info.edition}  modules: {', '.join(info.modules)}")
    print(f"branches: {info.max_branches or 'unlimited'}  maintenance until: {info.maintenance_until}"
          f"  AI until: {info.ai_until or '—'}")
    print(f"written: {lic_path}")
    print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
