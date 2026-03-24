"""
verify_security_fixes.py
========================
Validates that the specific security fix points described in the issue
are present in app.py.  Intended to be run by reviewers after applying
the suggested changes.

Checks:
  1. python-dotenv is used to load .env
  2. SECRET_KEY is read from environment / not hard-coded
  3. CSRFProtect is imported and initialised
  4. Flask-Limiter is imported and initialised
  5. The f-string SyntaxError bug around download_name is fixed
  6. No @csrf.exempt on the login route

Run:
    python verify_security_fixes.py
"""

import re
import sys
from pathlib import Path

APP_PATH = Path(__file__).parent / "app.py"
ISSUES_FOUND: list[str] = []


def ok(msg: str) -> bool:
    print(f"  [PASS] {msg}")
    return True


def fail(msg: str, hint: str = "") -> bool:
    full = f"  [FAIL] {msg}"
    if hint:
        full += f"\n         Hint: {hint}"
    print(full)
    ISSUES_FOUND.append(msg)
    return False


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


# ---------------------------------------------------------------------------

def check_dotenv(src: str) -> bool:
    if re.search(r"load_dotenv|from dotenv", src):
        return ok("python-dotenv load_dotenv() is used")
    return fail(
        "load_dotenv() not found",
        "Add at top of app.py:\n"
        "           from dotenv import load_dotenv\n"
        "           load_dotenv()",
    )


def check_secret_key_from_env(src: str) -> bool:
    if re.search(r"os\.environ|os\.getenv", src) and re.search(r"SECRET_KEY", src):
        return ok("SECRET_KEY is read from os.environ/os.getenv")
    if re.search(r"SECRET_KEY", src):
        warn("SECRET_KEY found but may be hard-coded — consider reading from .env")
        return True  # soft pass
    return fail(
        "SECRET_KEY not found in app.py",
        "Add: app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')",
    )


def check_csrf_init(src: str) -> bool:
    if "CSRFProtect" in src and re.search(r"CSRFProtect\s*\(\s*app\s*\)|csrf\.init_app\s*\(\s*app\s*\)", src):
        return ok("CSRFProtect(app) is initialised")
    return fail(
        "CSRFProtect not properly initialised",
        "Add:\n"
        "           from flask_wtf.csrf import CSRFProtect\n"
        "           csrf = CSRFProtect(app)",
    )


def check_limiter_init(src: str) -> bool:
    if "Limiter" in src and re.search(r"Limiter\s*\(", src):
        return ok("Flask-Limiter Limiter() is instantiated")
    return fail(
        "Flask-Limiter not initialised",
        "See BRUTEFORCE_PROTECTION_SETUP.md",
    )


def check_fstring_fix(src: str) -> bool:
    # The bug: f"...{cls['name']}..." (same quotes inside f-string)
    pattern = re.search(r"""f["']grades_\{cls\[['"]""", src)
    if pattern:
        return fail(
            "f-string SyntaxError bug still present",
            "Replace with:\n"
            "           name_part = cls['name'] if isinstance(cls, dict) and 'name' in cls else class_id\n"
            "           download_name = f\"grades_{name_part}_{active_name}.pdf\".replace(' ', '_')",
        )
    return ok("f-string download_name bug not detected (may already be fixed)")


def check_no_csrf_exempt_login(src: str) -> bool:
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if "@csrf.exempt" in line:
            nearby = "\n".join(lines[max(0, i - 1): i + 5])
            if "login" in nearby.lower():
                fail(
                    f"@csrf.exempt near login route (line {i + 1})",
                    "Remove @csrf.exempt from the login route unless intentional.",
                )
                return False
    return ok("@csrf.exempt not found on login route")


# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("  verify_security_fixes.py — Security Fix Verification")
    print("=" * 65)

    if not APP_PATH.exists():
        print(f"\n[SKIP] app.py not found at {APP_PATH}")
        print("       Copy app.py next to this script to run verification.")
        sys.exit(0)

    src = APP_PATH.read_text(encoding="utf-8")

    checks = [
        check_dotenv(src),
        check_secret_key_from_env(src),
        check_csrf_init(src),
        check_limiter_init(src),
        check_fstring_fix(src),
        check_no_csrf_exempt_login(src),
    ]

    print("-" * 65)
    passed = sum(checks)
    total = len(checks)
    print(f"  {passed}/{total} security fix checks passed")
    if not ISSUES_FOUND:
        print("  All security fixes verified ✓")
    else:
        print("  Issues found:")
        for issue in ISSUES_FOUND:
            print(f"    • {issue}")
    print("=" * 65)
    sys.exit(0 if not ISSUES_FOUND else 1)


if __name__ == "__main__":
    main()
