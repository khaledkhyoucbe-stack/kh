"""
test_security_startup.py
========================
Performs startup security checks by importing the Flask application and
inspecting its configuration object.  The server does NOT need to be running.

Requirements:
  - app.py must be in the same directory (or on PYTHONPATH)
  - All dependencies must be installed (pip install -r requirements.txt)

Run:
    python test_security_startup.py
"""

import sys
import os
from pathlib import Path

APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

PASS = True
FAIL = False
results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, message: str = "") -> bool:
    status = PASS if condition else FAIL
    results.append((name, status, message))
    icon = "PASS" if condition else "FAIL"
    line = f"  [{icon}] {name}"
    if message:
        line += f"\n         {message}"
    print(line)
    return condition


# ---------------------------------------------------------------------------

def load_app():
    """Attempt to import the Flask app object from app.py."""
    try:
        import app as app_module  # type: ignore
        # Try common attribute names
        for attr in ("app", "application", "create_app"):
            if hasattr(app_module, attr):
                obj = getattr(app_module, attr)
                if callable(obj) and attr == "create_app":
                    obj = obj()
                return obj
        print("[WARN] Could not locate Flask app object in app.py "
              "(expected 'app', 'application', or 'create_app')")
        return None
    except SyntaxError as exc:
        print(f"[FAIL] SyntaxError in app.py: {exc}")
        print("       Fix the SyntaxError before running this script.")
        return None
    except ImportError as exc:
        print(f"[WARN] ImportError loading app.py: {exc}")
        print("       Install missing packages with: pip install -r requirements.txt")
        return None
    except Exception as exc:
        print(f"[WARN] Could not import app.py: {exc}")
        return None


def run_config_checks(flask_app) -> None:
    cfg = flask_app.config

    # SECRET_KEY
    sk = cfg.get("SECRET_KEY", "")
    check(
        "SECRET_KEY is set",
        bool(sk and sk != "dev-secret-change-me" and len(str(sk)) >= 16),
        "Set SECRET_KEY in .env to a strong random value (e.g. python -c \"import secrets; print(secrets.token_hex(32))\")"
        if not sk else "",
    )

    # WTF_CSRF_ENABLED
    csrf_enabled = cfg.get("WTF_CSRF_ENABLED", True)
    check(
        "WTF_CSRF_ENABLED is True (or not explicitly disabled)",
        csrf_enabled is not False,
        "Remove WTF_CSRF_ENABLED = False from app configuration" if not csrf_enabled else "",
    )

    # DEBUG should be off in production
    debug = cfg.get("DEBUG", False)
    if debug:
        check(
            "DEBUG mode is off",
            False,
            "Set DEBUG=False before deploying to production",
        )
    else:
        check("DEBUG mode is off", True)

    # SESSION_COOKIE_SECURE (recommended for HTTPS)
    secure = cfg.get("SESSION_COOKIE_SECURE", False)
    check(
        "SESSION_COOKIE_SECURE is set",
        secure,
        "Set SESSION_COOKIE_SECURE=True for HTTPS deployments",
    ) if not secure else check("SESSION_COOKIE_SECURE is set", True)

    # SESSION_COOKIE_HTTPONLY
    httponly = cfg.get("SESSION_COOKIE_HTTPONLY", True)
    check(
        "SESSION_COOKIE_HTTPONLY is True",
        httponly is not False,
        "Set SESSION_COOKIE_HTTPONLY=True to prevent XSS token theft",
    )


def run_without_app() -> None:
    """Fallback checks when app.py cannot be imported."""
    app_py = APP_DIR / "app.py"
    if not app_py.exists():
        check("app.py exists", False, "Place app.py in the same directory")
        return

    src = app_py.read_text(encoding="utf-8")

    import re
    check("SECRET_KEY in app.py", "SECRET_KEY" in src)
    check("CSRFProtect in app.py", "CSRFProtect" in src)
    check("Limiter in app.py", "Limiter" in src)
    check("load_dotenv in app.py", "load_dotenv" in src,
          "Add: from dotenv import load_dotenv; load_dotenv()")


# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  test_security_startup.py — Flask Security Startup Check")
    print("=" * 60)

    flask_app = load_app()
    if flask_app is not None:
        print(f"\n[INFO] Loaded Flask app: {flask_app.name}\n")
        run_config_checks(flask_app)
    else:
        print("\n[INFO] Falling back to source-code checks (app not importable)\n")
        run_without_app()

    print("-" * 60)
    passed = sum(1 for _, s, _ in results if s)
    failed = sum(1 for _, s, _ in results if not s)
    print(f"  Passed: {passed}  Failed: {failed}")
    if failed == 0:
        print("  Startup security checks OK ✓")
    else:
        print("  Issues found — review messages above")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
