"""
tools/login_flood.py
====================
Stress-tests the rate limiter by sending repeated login requests.
Should trigger a 429 Too Many Requests response once the limit is exceeded.

Usage:
    python tools/login_flood.py [--base-url http://127.0.0.1:5000]
                                [--count 20]
                                [--delay 0.1]

WARNING:
    Only run this against a development server that you own.
    Never use this against production systems.
"""

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
except ImportError:
    print("[ERROR] Install requests: pip install requests")
    sys.exit(1)

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10


def get_csrf_token(session: requests.Session, base_url: str) -> str | None:
    try:
        resp = session.get(f"{base_url}/login", timeout=TIMEOUT)
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to {base_url}. Start the Flask server first.")
        return None
    for pattern in [
        r'<input[^>]+name=["\']csrf_token["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']csrf_token["\']',
    ]:
        m = re.search(pattern, resp.text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def flood(base_url: str, count: int, delay: float) -> None:
    print("=" * 60)
    print("  Login Flood Test — Rate Limiter Verification")
    print(f"  Target : {base_url}/login")
    print(f"  Requests: {count}  |  Delay between requests: {delay}s")
    print("=" * 60)
    print("[WARN] Only use against your own development server!\n")

    status_counts: dict[int, int] = {}

    for i in range(1, count + 1):
        # Each request uses a fresh session to simulate different users
        # (some rate limiters are per-IP, so same IP will still be limited)
        session = requests.Session()
        token = get_csrf_token(session, base_url)
        if token is None and i == 1:
            print("[FAIL] Could not start — cannot retrieve CSRF token")
            return

        payload = {
            "csrf_token": token or "",
            "username": f"flood_user_{i}",
            "password": "wrong_password",
        }
        try:
            resp = session.post(
                f"{base_url}/login",
                data=payload,
                timeout=TIMEOUT,
                allow_redirects=False,
            )
        except requests.exceptions.ConnectionError:
            print(f"  Request {i:3d}: [ERROR] connection lost")
            break

        code = resp.status_code
        status_counts[code] = status_counts.get(code, 0) + 1

        if code == 429:
            retry_after = resp.headers.get("Retry-After", "?")
            print(f"  Request {i:3d}: HTTP 429 — Rate Limited ✓  (Retry-After: {retry_after}s)")
        elif code == 400:
            print(f"  Request {i:3d}: HTTP 400 — CSRF rejected")
        elif code in (200, 302):
            print(f"  Request {i:3d}: HTTP {code}")
        else:
            print(f"  Request {i:3d}: HTTP {code}")

        if delay > 0:
            time.sleep(delay)

    print("\n" + "-" * 60)
    print("  Summary:")
    for code, cnt in sorted(status_counts.items()):
        label = {
            200: "OK",
            302: "Redirect",
            400: "Bad Request (CSRF rejected)",
            429: "Too Many Requests (rate limited)",
        }.get(code, "")
        print(f"    HTTP {code} ({label}): {cnt} times")

    if 429 in status_counts:
        print("\n  [OK] Rate limiter is working — 429 responses received ✓")
    else:
        print("\n  [WARN] No 429 responses received.")
        print("         Either the rate limit is higher than the request count,")
        print("         or Flask-Limiter is not configured.")
        print("         See BRUTEFORCE_PROTECTION_SETUP.md for setup instructions.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Login flood test for rate limiter")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--count", type=int, default=20,
                        help="Number of login requests to send (default: 20)")
    parser.add_argument("--delay", type=float, default=0.1,
                        help="Seconds to wait between requests (default: 0.1)")
    args = parser.parse_args()

    flood(args.base_url, args.count, args.delay)


if __name__ == "__main__":
    main()
