"""
test_csrf_fix.py
================
Fetches the /login page, extracts the CSRF token, then POSTs login
credentials to verify that CSRF protection is working correctly.

Usage:
    python test_csrf_fix.py [--base-url http://127.0.0.1:5000]
"""

import argparse
import sys
import re

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' package is not installed. Run: pip install requests")
    sys.exit(1)

DEFAULT_BASE_URL = "http://127.0.0.1:5000"


def get_csrf_token(session: requests.Session, base_url: str) -> str | None:
    """
    GET /login and extract the CSRF token from the HTML form.
    Returns the token string or None if not found.
    """
    login_url = f"{base_url}/login"
    print(f"[INFO] GET {login_url}")
    try:
        resp = session.get(login_url, timeout=10)
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Could not connect to {login_url}. Is the server running?")
        return None

    if resp.status_code != 200:
        print(f"[WARN] GET /login returned HTTP {resp.status_code}")

    # Search for a hidden CSRF input field (Flask-WTF default name: csrf_token)
    patterns = [
        r'<input[^>]+name=["\']csrf_token["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']csrf_token["\']',
        r'csrf_token["\']:\s*["\']([^"\']+)["\']',  # JSON or JS variable
    ]
    for pattern in patterns:
        match = re.search(pattern, resp.text, re.IGNORECASE)
        if match:
            token = match.group(1)
            print(f"[OK]   CSRF token found: {token[:20]}…")
            return token

    print("[FAIL] CSRF token NOT found in /login response.")
    print("       Check that {{ form.hidden_tag() }} or {{ form.csrf_token }} is in the template.")
    return None


def test_login_with_csrf(session: requests.Session, base_url: str,
                         username: str = "test_user",
                         password: str = "wrong_password") -> None:
    """POST to /login with a valid CSRF token and report the result."""
    csrf_token = get_csrf_token(session, base_url)
    if csrf_token is None:
        print("[SKIP] Cannot POST without a CSRF token.")
        return

    login_url = f"{base_url}/login"
    payload = {
        "csrf_token": csrf_token,
        "username": username,
        "password": password,
    }
    print(f"[INFO] POST {login_url} (username={username!r})")
    resp = session.post(login_url, data=payload, timeout=10, allow_redirects=False)

    print(f"[INFO] Response: HTTP {resp.status_code}")
    if resp.status_code in (200, 302):
        if "Bad Request" in resp.text or "CSRF" in resp.text:
            print("[FAIL] Server still rejected the request with a CSRF error.")
        elif resp.status_code == 302:
            print(f"[OK]   Redirect to: {resp.headers.get('Location', '?')} "
                  "(likely successful login or wrong-credentials redirect)")
        else:
            print("[OK]   200 OK received (check page content for error messages).")
    elif resp.status_code == 400:
        print("[FAIL] 400 Bad Request — CSRF token was rejected by the server.")
        print("       Possible causes:")
        print("         - SECRET_KEY changes between requests (check app.py)")
        print("         - Session cookie not sent (check requests.Session usage)")
        print("         - CSRF token field name mismatch")
    else:
        print(f"[WARN] Unexpected status code: {resp.status_code}")


def test_login_without_csrf(session: requests.Session, base_url: str) -> None:
    """POST to /login WITHOUT a CSRF token — should be rejected with 400."""
    login_url = f"{base_url}/login"
    payload = {"username": "test_user", "password": "wrong_password"}
    print(f"\n[INFO] POST {login_url} WITHOUT csrf_token (should be rejected)")
    resp = session.post(login_url, data=payload, timeout=10, allow_redirects=False)
    print(f"[INFO] Response: HTTP {resp.status_code}")
    if resp.status_code == 400:
        print("[OK]   400 Bad Request — CSRF protection is active (expected).")
    elif resp.status_code in (200, 302):
        print("[WARN] Server accepted a request without a CSRF token.")
        print("       Verify that CSRFProtect(app) is initialised and "
              "@csrf.exempt is not set on the login route.")
    else:
        print(f"[INFO] Status {resp.status_code} — review manually.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test CSRF protection on /login")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help="Base URL of the Flask application")
    parser.add_argument("--username", default="test_user")
    parser.add_argument("--password", default="wrong_password")
    args = parser.parse_args()

    print("=" * 60)
    print("  CSRF Fix Verification Script")
    print("=" * 60)

    session = requests.Session()

    print("\n--- Test 1: Login WITH valid CSRF token ---")
    test_login_with_csrf(session, args.base_url, args.username, args.password)

    print("\n--- Test 2: Login WITHOUT CSRF token (should fail) ---")
    test_login_without_csrf(session, args.base_url)

    print("\n" + "=" * 60)
    print("  Done. Review results above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
