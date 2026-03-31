"""
test_csrf_config.py
===================
Validates the security configuration of app.py:
  - SECRET_KEY is set and non-trivial
  - CSRFProtect is initialised
  - Flask-Limiter is configured
  - WTF_CSRF_ENABLED is not explicitly disabled

Run:
    python test_csrf_config.py
"""

import sys
import os
import ast
import re
from pathlib import Path

APP_PATH = Path(__file__).parent / "app.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_app_source() -> str | None:
    if not APP_PATH.exists():
        print(f"[SKIP] app.py not found at {APP_PATH} — skipping source checks.")
        return None
    return APP_PATH.read_text(encoding="utf-8")


def check_secret_key(source: str) -> bool:
    """Warn if SECRET_KEY is hard-coded to a trivial value."""
    # Accept os.environ / os.getenv / dotenv patterns
    if re.search(r"os\.environ|os\.getenv|load_dotenv|dotenv", source):
        print("[OK] SECRET_KEY appears to be read from environment or .env")
        return True
    if re.search(r"SECRET_KEY", source):
        # Key exists but may be hard-coded; warn rather than fail
        match = re.search(r"SECRET_KEY['\"]?\s*[=:]\s*['\"]([^'\"]{0,40})['\"]", source)
        if match:
            val = match.group(1)
            trivial = {"", "dev", "secret", "changeme", "dev-secret-change-me"}
            if val.lower() in trivial or len(val) < 16:
                print(f"[WARN] SECRET_KEY value looks weak or trivial: {val!r}")
                print("       Use a strong random key loaded from os.environ or .env")
                return False
        print("[OK] SECRET_KEY is defined in app.py")
        return True
    print("[FAIL] SECRET_KEY not found in app.py")
    print("       Add: app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me')")
    return False


def check_csrf_protect(source: str) -> bool:
    has_import = "CSRFProtect" in source
    has_init = bool(re.search(r"CSRFProtect\s*\(\s*app\s*\)", source) or
                    re.search(r"csrf\.init_app\s*\(\s*app\s*\)", source))
    if has_import and has_init:
        print("[OK] CSRFProtect is imported and initialised")
        return True
    if has_import and not has_init:
        print("[WARN] CSRFProtect is imported but not initialised with app")
        print("       Add: csrf = CSRFProtect(app)  after app = Flask(__name__)")
        return False
    print("[FAIL] CSRFProtect not found in app.py")
    print("       Add: from flask_wtf.csrf import CSRFProtect")
    print("            csrf = CSRFProtect(app)")
    return False


def check_csrf_not_disabled(source: str) -> bool:
    if re.search(r"WTF_CSRF_ENABLED\s*[=:]\s*False", source, re.IGNORECASE):
        print("[FAIL] WTF_CSRF_ENABLED is set to False — CSRF protection is disabled!")
        return False
    print("[OK] WTF_CSRF_ENABLED is not disabled")
    return True


def check_csrf_exempt_on_login(source: str) -> bool:
    """Warn if the login route has @csrf.exempt."""
    pattern = re.compile(
        r"@csrf\.exempt\s*\n\s*@.*?(?:route|login|sign)",
        re.DOTALL | re.IGNORECASE,
    )
    # Simpler: look for @csrf.exempt close to a login function
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if "@csrf.exempt" in line:
            context = "\n".join(lines[max(0, i-1): i+4])
            if "login" in context.lower():
                print(f"[WARN] @csrf.exempt found near a 'login' route (line {i+1}):")
                print(f"       {context}")
                print("       Unless intentional, remove @csrf.exempt from the login route.")
                return False
            else:
                print(f"[INFO] @csrf.exempt used at line {i+1} (not near 'login') — review manually.")
    print("[OK] No @csrf.exempt on login route detected")
    return True


def check_limiter(source: str) -> bool:
    has_import = "Limiter" in source and "flask_limiter" in source
    has_init = bool(re.search(r"Limiter\s*\(", source))
    if has_import and has_init:
        print("[OK] Flask-Limiter is imported and instantiated")
        return True
    if has_import and not has_init:
        print("[WARN] Flask-Limiter is imported but not instantiated")
        return False
    print("[WARN] Flask-Limiter not found in app.py")
    print("       See BRUTEFORCE_PROTECTION_SETUP.md for setup instructions")
    return False


def check_fstring_bug(source: str) -> bool:
    """
    Detect the known f-string bug:
        f"grades_{cls['name']}_{active_name}.pdf"
    Python 3.11 and earlier do not allow the same quote inside the f-string
    expression; this will raise a SyntaxError.
    """
    pattern = re.search(r"""f["']grades_\{cls\[['"]""", source)
    if pattern:
        print("[FAIL] Potential f-string SyntaxError detected:")
        print("       Suggested fix:")
        print("         name_part = cls['name'] if isinstance(cls, dict) and 'name' in cls else class_id")
        print("         download_name = f\"grades_{name_part}_{active_name}.pdf\".replace(' ', '_')")
        return False
    print("[OK] No f-string dict-access SyntaxError detected")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  CSRF & Security Configuration Check (app.py)")
    print("=" * 60)

    source = read_app_source()
    if source is None:
        print("\n[NOTE] Place app.py next to this script to run source checks.")
        sys.exit(0)

    results = [
        check_secret_key(source),
        check_csrf_protect(source),
        check_csrf_not_disabled(source),
        check_csrf_exempt_on_login(source),
        check_limiter(source),
        check_fstring_bug(source),
    ]

    print("-" * 60)
    passed = sum(results)
    total = len(results)
    print(f"  {passed}/{total} checks passed")
    if passed == total:
        print("  All configuration checks OK ✓")
    else:
        print("  Issues found — review messages above and update app.py")
    print("=" * 60)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
