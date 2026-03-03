#!/usr/bin/env python3
"""Module overview for scripts/secure_codex_key.py.
This module is part of LaunchPad Conversion Lab and contains runtime logic
for the feature area represented by this file path.
"""
from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
SECRETS_DIR = ROOT / ".secrets"
DECRYPTION_KEY_FILE = SECRETS_DIR / "codex_decryption.key"


def parse_env(path: Path) -> dict[str, str]:
    """Execute the parse env workflow. This function is part of the module-level runtime flow."""
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k] = v
    return data


def write_env_preserving_order(path: Path, updates: dict[str, str]) -> None:
    """Execute the write env preserving order workflow. This function is part of the module-level runtime flow."""
    lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    out: list[str] = []

    for line in lines:
        if not line or line.strip().startswith("#") or "=" not in line:
            out.append(line)
            continue
        key, _ = line.split("=", 1)
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)

    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    """Execute the main workflow. This function is part of the module-level runtime flow."""
    if not ENV_PATH.exists():
        raise SystemExit(".env not found")

    env = parse_env(ENV_PATH)
    plain = env.get("CODEX_API_KEY", "").strip()
    if not plain:
        raise SystemExit("CODEX_API_KEY is empty in .env; nothing to secure")

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    fernet_key = Fernet.generate_key()
    cipher = Fernet(fernet_key).encrypt(plain.encode("utf-8")).decode("utf-8")

    DECRYPTION_KEY_FILE.write_text(fernet_key.decode("utf-8") + "\n", encoding="utf-8")

    updates = {
        "CODEX_API_KEY": "",
        "CODEX_API_KEY_ENCRYPTED": cipher,
        "CODEX_API_KEY_DECRYPTION_KEY": "",
        "CODEX_API_KEY_DECRYPTION_KEY_FILE": str(DECRYPTION_KEY_FILE),
    }
    write_env_preserving_order(ENV_PATH, updates)

    print("Secured CODEX_API_KEY: plaintext removed from .env")
    print(f"Decryption key file: {DECRYPTION_KEY_FILE}")


if __name__ == "__main__":
    main()
