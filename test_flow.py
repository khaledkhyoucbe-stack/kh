"""
test_flow.py
============
End-to-end login flow test against a running Flask server.

Steps:
  1. GET /login                  → expect 200, check for CSRF token in HTML
  2. POST /login (bad password)  → expect redirect or 200 with error message
  3. POST /login (no CSRF)       → expect 400

Run:
    python test_flow.py [--base-url http://127.0.0.1:5000]
"""

import argparse
import sys
import re

try:
    import requests
except ImportError:
    print("[ERROR] Install requests: pip install requests")
    sys.exit(1)

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10

RESULT_PASS = "PASS"
RESULT_FAIL = "FAIL"
RESULT_WARN = "WARN"
RESULT_SKIP = "SKIP"


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.status = RESULT_SKIP
        self.message = ""

    def passed(self, msg: str = ""):
        self.status = RESULT_PASS
        self.message = msg
        return self

    def failed(self, msg: str = ""):
        self.status = RESULT_FAIL
        self.message = msg
        return self

    def warn(self, msg: str = ""):
        self.status = RESULT_WARN
        self.message = msg
        return self

    def __str__(self):
        icon = {"PASS": "✓", "FAIL": "✗", "WARN": "!", "SKIP": "-"}[self.status]
        line = f"  [{icon}] {self.name}"
        if self.message:
            line += f"\n      {self.message}"
        return line


def extract_csrf_token(html: str) -> str | None:
    for pattern in [
        r'<input[^>]+name=["\']csrf_token["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']+)["\'][^>]+name=["\']csrf_token["\']',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def run_tests(base_url: str) -> list[TestResult]:
    results: list[TestResult] = []
    session = requests.Session()

    # ------------------------------------------------------------------
    # Test 1: GET /login returns 200
    # ------------------------------------------------------------------
    r1 = TestResult("GET /login returns 200")
    try:
        resp = session.get(f"{base_url}/login", timeout=TIMEOUT)
        if resp.status_code == 200:
            r1.passed(f"HTTP 200 OK ({len(resp.text)} bytes)")
        else:
            r1.failed(f"HTTP {resp.status_code}")
    except requests.exceptions.ConnectionError:
        r1.failed(f"Connection refused — is the server running at {base_url}?")
        results.append(r1)
        # No point running further tests
        return results
    results.append(r1)
    login_html = resp.text

    # ------------------------------------------------------------------
    # Test 2: CSRF token present in /login page
    # ------------------------------------------------------------------
    r2 = TestResult("CSRF token present in login page HTML")
    csrf_token = extract_csrf_token(login_html)
    if csrf_token:
        r2.passed(f"Token: {csrf_token[:20]}…")
    else:
        r2.failed("No csrf_token input found in /login HTML. "
                  "Add {{ form.hidden_tag() }} to the template.")
    results.append(r2)

    # ------------------------------------------------------------------
    # Test 3: POST /login WITH CSRF token (wrong credentials)
    #         Expected: 200 with error message OR redirect
    # ------------------------------------------------------------------
    r3 = TestResult("POST /login with CSRF token (wrong credentials)")
    if csrf_token:
        payload = {"csrf_token": csrf_token, "username": "nouser", "password": "badpass"}
        resp3 = session.post(f"{base_url}/login", data=payload, timeout=TIMEOUT,
                             allow_redirects=False)
        if resp3.status_code == 400 and ("CSRF" in resp3.text or "Bad Request" in resp3.text):
            r3.failed(f"HTTP 400 — CSRF token rejected even though it was sent. "
                      f"Check SECRET_KEY consistency and session cookie handling.")
        elif resp3.status_code in (200, 302):
            r3.passed(f"HTTP {resp3.status_code} — request accepted (credentials rejected, "
                      f"not the CSRF check)")
        else:
            r3.warn(f"HTTP {resp3.status_code} — review manually")
    else:
        r3 = TestResult("POST /login with CSRF token (skipped — no token found)")
    results.append(r3)

    # ------------------------------------------------------------------
    # Test 4: POST /login WITHOUT CSRF token → must return 400
    # ------------------------------------------------------------------
    r4 = TestResult("POST /login WITHOUT CSRF token should return 400")
    # Use a fresh session so there is no CSRF cookie either
    bare_session = requests.Session()
    resp4 = bare_session.post(f"{base_url}/login",
                              data={"username": "x", "password": "y"},
                              timeout=TIMEOUT, allow_redirects=False)
    if resp4.status_code == 400:
        r4.passed("HTTP 400 — CSRF protection active ✓")
    elif resp4.status_code in (200, 302):
        r4.failed(f"HTTP {resp4.status_code} — Server accepted request without CSRF token! "
                  "Ensure CSRFProtect(app) is initialised and login route is not @csrf.exempt.")
    else:
        r4.warn(f"HTTP {resp4.status_code} — review manually")
    results.append(r4)

    return results


def main():
    parser = argparse.ArgumentParser(description="End-to-end login/CSRF flow test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    print("=" * 60)
    print("  End-to-End Login / CSRF Flow Test")
    print(f"  Target: {args.base_url}")
    print("=" * 60)

    results = run_tests(args.base_url)
    for r in results:
        print(r)

    print("-" * 60)
    passed = sum(1 for r in results if r.status == RESULT_PASS)
    failed = sum(1 for r in results if r.status == RESULT_FAIL)
    warned = sum(1 for r in results if r.status == RESULT_WARN)
    print(f"  Passed: {passed}  Failed: {failed}  Warnings: {warned}")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
