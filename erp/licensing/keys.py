"""License-signing PUBLIC keys (base64url, raw 32-byte Ed25519). Safe to commit — public by design.

Empty until the founder generates the real keypair on their own machine:

    python tools/license/issue_license.py --new-keypair --out <path outside the repo>

then pastes the printed public key here. The matching private key must never be committed or
copied to a customer server. More than one entry = key rotation: keys signed by any listed key
verify, so a new key can be added before the old one is retired.
"""

PUBLIC_KEYS: tuple[str, ...] = ()
