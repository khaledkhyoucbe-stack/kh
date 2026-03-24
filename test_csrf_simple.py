"""
test_csrf_simple.py
===================
Quick smoke test — verifies that the Flask-WTF CSRF package can be imported
and that CSRFProtect can be instantiated with a minimal Flask app.

Run:
    python test_csrf_simple.py
"""

import sys


def test_import_flask():
    try:
        import flask  # noqa: F401
        print(f"[OK] flask {flask.__version__} imported successfully")
        return True
    except ImportError as exc:
        print(f"[FAIL] flask import failed: {exc}")
        return False


def test_import_flask_wtf():
    try:
        from flask_wtf.csrf import CSRFProtect  # noqa: F401
        print("[OK] flask_wtf.csrf.CSRFProtect imported successfully")
        return True
    except ImportError as exc:
        print(f"[FAIL] flask_wtf import failed: {exc}")
        print("       Fix: pip install flask-wtf")
        return False


def test_import_flask_limiter():
    try:
        from flask_limiter import Limiter  # noqa: F401
        from flask_limiter.util import get_remote_address  # noqa: F401
        print("[OK] flask_limiter imported successfully")
        return True
    except ImportError as exc:
        print(f"[FAIL] flask_limiter import failed: {exc}")
        print("       Fix: pip install flask-limiter")
        return False


def test_import_dotenv():
    try:
        from dotenv import load_dotenv  # noqa: F401
        print("[OK] python-dotenv imported successfully")
        return True
    except ImportError as exc:
        print(f"[FAIL] python-dotenv import failed: {exc}")
        print("       Fix: pip install python-dotenv")
        return False


def test_csrf_protect_init():
    """Create a minimal Flask app and attach CSRFProtect to it."""
    try:
        from flask import Flask
        from flask_wtf.csrf import CSRFProtect

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
        _csrf = CSRFProtect(app)  # noqa: F841
        print("[OK] CSRFProtect initialised on a Flask app without errors")
        return True
    except Exception as exc:
        print(f"[FAIL] CSRFProtect init raised: {exc}")
        return False


def main():
    print("=" * 55)
    print("  Simple CSRF Import & Init Test")
    print("=" * 55)
    results = [
        test_import_flask(),
        test_import_flask_wtf(),
        test_import_flask_limiter(),
        test_import_dotenv(),
        test_csrf_protect_init(),
    ]
    print("-" * 55)
    passed = sum(results)
    total = len(results)
    print(f"  {passed}/{total} checks passed")
    if passed == total:
        print("  All checks OK ✓")
    else:
        print("  Some checks FAILED — see messages above")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
