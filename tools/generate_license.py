#!/usr/bin/env python3
"""
PaddiSense License Key Generator - ADMIN USE ONLY

This tool generates signed license keys for PaddiSense deployments.
Keep the private key secure - never distribute it.

Usage:
    # First-time: Generate a new keypair
    python generate_license.py init

    # Generate a license key for a grower (includes GitHub token for repo access)
    python generate_license.py generate \
        --key ~/secrets/paddisense_private.pem \
        --grower "John Smith" \
        --farm "River Farm" \
        --season "2026-WS" \
        --months 6 \
        --modules ipm asm weather \
        --token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import date, timedelta
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
        load_pem_private_key,
    )
except ImportError:
    print("Error: cryptography package not installed.")
    print("Install with: pip install cryptography")
    sys.exit(1)


def generate_keypair(output_dir: str | None = None) -> None:
    """Generate a new Ed25519 keypair for license signing."""
    private_key = Ed25519PrivateKey.generate()

    private_pem = private_key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        private_path = output_path / "private.pem"
        public_path = output_path / "public.pem"

        private_path.write_bytes(private_pem)
        private_path.chmod(0o600)  # Owner read/write only
        public_path.write_bytes(public_pem)

        print(f"Private key saved to: {private_path}")
        print(f"Public key saved to: {public_path}")
        print("")
        print("IMPORTANT:")
        print("  - Keep private.pem secure - never commit to git or share")
        print("  - Copy public.pem to custom_components/paddisense/keys/")
    else:
        print("=" * 60)
        print("PRIVATE KEY - Keep this secret! Never share or commit to git.")
        print("=" * 60)
        print(private_pem.decode())
        print("")
        print("=" * 60)
        print("PUBLIC KEY - Copy to custom_components/paddisense/keys/public.pem")
        print("=" * 60)
        print(public_pem.decode())


def generate_license(
    private_key_path: str,
    grower: str,
    farm: str,
    season: str,
    months: int,
    modules: list[str],
    github_token: str,
) -> str:
    """Generate a signed license key."""
    key_path = Path(private_key_path)
    if not key_path.exists():
        print(f"Error: Private key not found at {private_key_path}")
        sys.exit(1)

    # Load private key
    private_key = load_pem_private_key(key_path.read_bytes(), password=None)

    # Calculate expiry date
    expiry_date = date.today() + timedelta(days=months * 30)

    # Build payload
    payload = {
        "grower": grower,
        "farm": farm,
        "season": season,
        "expiry": expiry_date.isoformat(),
        "modules": modules,
        "issued": date.today().isoformat(),
        "github_token": github_token,
    }

    # Encode payload as compact JSON
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()

    # Sign the payload
    signature = private_key.sign(payload_bytes)
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    # Construct the license key
    license_key = f"PADDISENSE.{payload_b64}.{signature_b64}"

    # Display result (mask token for security)
    token_display = f"{github_token[:10]}...{github_token[-4:]}" if len(github_token) > 14 else "***"
    print("")
    print("=" * 60)
    print(f"LICENSE KEY for {grower}")
    print("=" * 60)
    print(f"Farm:    {farm}")
    print(f"Season:  {season}")
    print(f"Expires: {expiry_date.isoformat()}")
    print(f"Modules: {', '.join(modules)}")
    print(f"Token:   {token_display}")
    print("")
    print("License Key:")
    print("-" * 60)
    print(license_key)
    print("-" * 60)
    print("")
    print("Send this key to the grower. They will enter it during setup.")
    print("")

    return license_key


def verify_license(public_key_path: str, license_key: str) -> None:
    """Verify a license key (for testing)."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key_path = Path(public_key_path)
    if not key_path.exists():
        print(f"Error: Public key not found at {public_key_path}")
        sys.exit(1)

    if not license_key.startswith("PADDISENSE."):
        print("Error: Invalid license format (missing prefix)")
        sys.exit(1)

    try:
        parts = license_key[len("PADDISENSE.") :].split(".")
        if len(parts) != 2:
            print("Error: Invalid license format (wrong structure)")
            sys.exit(1)

        payload_b64, signature_b64 = parts

        # Decode
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
        signature = base64.urlsafe_b64decode(signature_b64 + "==")

        # Load public key and verify
        public_key = load_pem_public_key(key_path.read_bytes())
        public_key.verify(signature, payload_bytes)

        # Parse and display
        data = json.loads(payload_bytes.decode("utf-8"))

        print("")
        print("License VALID")
        print("=" * 40)
        print(f"Grower:  {data.get('grower')}")
        print(f"Farm:    {data.get('farm')}")
        print(f"Season:  {data.get('season')}")
        print(f"Expiry:  {data.get('expiry')}")
        print(f"Modules: {', '.join(data.get('modules', []))}")
        print(f"Issued:  {data.get('issued')}")
        token = data.get('github_token')
        if token:
            token_display = f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "***"
            print(f"Token:   {token_display}")
        else:
            print("Token:   (not included)")

        # Check expiry
        expiry = date.fromisoformat(data["expiry"])
        if date.today() > expiry:
            print("")
            print("WARNING: This license has EXPIRED")
        else:
            days_left = (expiry - date.today()).days
            print(f"Days remaining: {days_left}")

    except Exception as e:
        print(f"Error: License verification failed - {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PaddiSense License Key Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate new keypair (first-time setup)
  python generate_license.py init
  python generate_license.py init --output ~/paddisense-keys

  # Generate license for a grower (includes GitHub token)
  python generate_license.py generate \\
      --key ~/secrets/private.pem \\
      --grower "John Smith" \\
      --farm "River Farm" \\
      --season "2026-WS" \\
      --months 6 \\
      --modules ipm asm weather pwm \\
      --token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

  # Verify a license key
  python generate_license.py verify \\
      --key ~/paddisense-keys/public.pem \\
      --license "PADDISENSE.eyJncm93..."
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command - generate keypair
    init_parser = subparsers.add_parser("init", help="Generate new Ed25519 keypair")
    init_parser.add_argument(
        "--output",
        "-o",
        help="Output directory for keys (if not specified, prints to stdout)",
    )

    # Generate command - create license
    gen_parser = subparsers.add_parser("generate", help="Generate a license key")
    gen_parser.add_argument(
        "--key", "-k", required=True, help="Path to private key (PEM format)"
    )
    gen_parser.add_argument(
        "--grower", "-g", required=True, help="Grower name (e.g., 'John Smith')"
    )
    gen_parser.add_argument(
        "--farm", "-f", required=True, help="Farm name (e.g., 'River Farm')"
    )
    gen_parser.add_argument(
        "--season",
        "-s",
        required=True,
        help="Season identifier (e.g., '2026-WS' for 2026 wet season)",
    )
    gen_parser.add_argument(
        "--months",
        "-m",
        type=int,
        default=6,
        help="License validity in months (default: 6)",
    )
    gen_parser.add_argument(
        "--modules",
        nargs="+",
        default=["ipm", "asm", "weather", "pwm"],
        help="Licensed modules (default: all)",
    )
    gen_parser.add_argument(
        "--token",
        "-t",
        required=True,
        help="GitHub Personal Access Token for repo access",
    )

    # Verify command - check license
    verify_parser = subparsers.add_parser("verify", help="Verify a license key")
    verify_parser.add_argument(
        "--key", "-k", required=True, help="Path to public key (PEM format)"
    )
    verify_parser.add_argument(
        "--license", "-l", required=True, help="License key to verify"
    )

    args = parser.parse_args()

    if args.command == "init":
        generate_keypair(args.output)
    elif args.command == "generate":
        generate_license(
            args.key, args.grower, args.farm, args.season, args.months, args.modules, args.token
        )
    elif args.command == "verify":
        verify_license(args.key, args.license)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
