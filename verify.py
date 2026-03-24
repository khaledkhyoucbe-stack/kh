"""
verify.py
=========
Quick verification that all required packages are installed and that
a minimal Flask app can start with CSRF protection and rate limiting.

Run:
    python verify.py
"""

import sys


def _import(package: str, import_path: str, pip_name: str) -> bool:
    try:
        __import__(import_path)
        mod = sys.modules[import_path]
        ver = getattr(mod, "__version__", "?")
        print(f"  [OK] {package} {ver}")
        return True
    except ImportError:
        print(f"  [FAIL] {package} not installed — run: pip install {pip_name}")
        return False


def check_imports() -> bool:
    print("Checking required packages:")
    results = [
        _import("flask",         "flask",              "flask"),
        _import("flask_wtf",     "flask_wtf",          "flask-wtf"),
        _import("flask_limiter", "flask_limiter",      "flask-limiter"),
        _import("dotenv",        "dotenv",             "python-dotenv"),
        _import("requests",      "requests",           "requests"),
        _import("wtforms",       "wtforms",            "wtforms"),
    ]
    return all(results)


def check_csrf_smoke_test() -> bool:
    print("\nRunning CSRF smoke test:")
    try:
        from flask import Flask
        from flask_wtf.csrf import CSRFProtect

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "verify-test-key-not-for-production"
        app.config["WTF_CSRF_ENABLED"] = True
        _csrf = CSRFProtect(app)  # noqa: F841

        with app.test_request_context():
            from flask_wtf.csrf import generate_csrf
            token = generate_csrf()
            assert token, "generate_csrf() returned empty string"
        print("  [OK] CSRFProtect initialised and generate_csrf() works")
        return True
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        return False


def check_limiter_smoke_test() -> bool:
    print("\nRunning Limiter smoke test:")
    try:
        from flask import Flask
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "verify-test-key-not-for-production"
        _limiter = Limiter(  # noqa: F841
            get_remote_address,
            app=app,
            default_limits=["200 per day", "50 per hour"],
        )
        print("  [OK] Flask-Limiter initialised with default limits")
        return True
    except Exception as exc:
        print(f"  [FAIL] {exc}")
        return False


def main():
    print("=" * 55)
    print("  verify.py — Environment & Security Smoke Test")
    print("=" * 55)

    ok_imports = check_imports()
    ok_csrf = check_csrf_smoke_test()
    ok_limiter = check_limiter_smoke_test()

    print("\n" + "=" * 55)
    all_ok = ok_imports and ok_csrf and ok_limiter
    if all_ok:
        print("  All checks passed ✓")
    else:
        print("  Some checks FAILED — review messages above")
    print("=" * 55)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
