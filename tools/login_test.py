"""
tools/login_test.py
===================
Single login request helper.
Sends one POST to /login and reports the outcome.

Usage:
    python tools/login_test.py [--base-url http://127.0.0.1:5000]
                               [--username admin]
                               [--password secret]
"""

import argparse
import re
import sys
from pathlib import Path

# Allow running from the project root or the tools/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import requests
except ImportError:
    print("[ERROR] Install requests: pip install requests")
    sys.exit(1)

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10


def get_csrf_token(session: requests.Session, base_url: str) -> str | None:
    """Fetch /login and extract the CSRF token."""
    try:
        resp = session.get(f"{base_url}/login", timeout=TIMEOUT)
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to {base_url}. Start the Flask server first.")
        return None
    if resp.status_code != 200:
        print(f"[WARN] GET /login returned HTTP {resp.status_code}")
    for pattern in [
        r'<input[^>]+name=["\']csrf_token["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']csrf_token["\']',
    ]:
        m = re.search(pattern, resp.text, re.IGNORECASE)
        if m:
            return m.group(1)
    print("[FAIL] CSRF token not found in /login page")
    return None


def login(base_url: str, username: str, password: str) -> None:
    session = requests.Session()
    print(f"[INFO] Connecting to {base_url}/login")

    token = get_csrf_token(session, base_url)
    if token is None:
        return

    print(f"[INFO] CSRF token: {token[:20]}…")
    print(f"[INFO] Attempting login as {username!r}")

    resp = session.post(
        f"{base_url}/login",
        data={"csrf_token": token, "username": username, "password": password},
        timeout=TIMEOUT,
        allow_redirects=False,
    )

    print(f"[INFO] Response: HTTP {resp.status_code}")
    if resp.status_code == 302:
        location = resp.headers.get("Location", "?")
        print(f"[OK]   Redirected to: {location}")
        if "login" in location.lower():
            print("       (Redirect back to /login — credentials likely incorrect)")
        else:
            print("       (Redirect to dashboard/home — login successful)")
    elif resp.status_code == 200:
        if "invalid" in resp.text.lower() or "incorrect" in resp.text.lower():
            print("[INFO] Login page re-rendered with error (invalid credentials)")
        elif "CSRF" in resp.text or "Bad Request" in resp.text:
            print("[FAIL] CSRF error in response body")
        else:
            print("[INFO] 200 OK (check page content)")
    elif resp.status_code == 400:
        print("[FAIL] 400 Bad Request — CSRF token rejected")
    elif resp.status_code == 429:
        print("[INFO] 429 Too Many Requests — rate limiter is active")
    else:
        print(f"[INFO] Unexpected status {resp.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Single login request test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="wrong_password")
    args = parser.parse_args()

    login(args.base_url, args.username, args.password)


if __name__ == "__main__":
    main()
