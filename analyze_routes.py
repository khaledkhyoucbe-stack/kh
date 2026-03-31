"""
analyze_routes.py
=================
Parses app.py and lists:
  1. All @app.route / @blueprint.route decorators and their HTTP methods
  2. All @csrf.exempt decorators (security audit)
  3. All Flask-Limiter @limiter.limit decorators
  4. All database table/model definitions (SQLAlchemy)
  5. The f-string download_name pattern (SyntaxError risk)

Run:
    python analyze_routes.py [--file app.py]
"""

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_source(path: Path) -> str | None:
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return None
    return path.read_text(encoding="utf-8")


def find_routes(source: str) -> list[dict]:
    """
    Find @app.route and @blueprint.route decorators.
    Returns list of dicts: {line, decorator, methods}
    """
    routes = []
    pattern = re.compile(
        r'@(?:\w+\.)+route\s*\(\s*["\']([^"\']+)["\'][^)]*\)',
        re.MULTILINE,
    )
    for m in pattern.finditer(source):
        line_num = source.count("\n", 0, m.start()) + 1
        # Extract methods= if present
        methods_match = re.search(r"methods\s*=\s*\[([^\]]+)\]", m.group(0))
        methods = methods_match.group(1) if methods_match else "GET"
        routes.append({
            "line": line_num,
            "path": m.group(1),
            "methods": methods.replace('"', "").replace("'", "").strip(),
            "raw": m.group(0),
        })
    return routes


def find_csrf_exempt(source: str) -> list[dict]:
    """Find @csrf.exempt decorators and the function they protect."""
    items = []
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if "@csrf.exempt" in line:
            # Look for the decorated function name
            func_name = "unknown"
            for j in range(i + 1, min(i + 5, len(lines))):
                fn_match = re.match(r"\s*def\s+(\w+)", lines[j])
                if fn_match:
                    func_name = fn_match.group(1)
                    break
            items.append({"line": i + 1, "function": func_name})
    return items


def find_limiter_limits(source: str) -> list[dict]:
    """Find @limiter.limit decorators."""
    items = []
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if "@limiter.limit" in line or "@limiter.shared_limit" in line:
            items.append({"line": i + 1, "decorator": line.strip()})
    return items


def find_models(source: str) -> list[dict]:
    """Find SQLAlchemy model class definitions."""
    items = []
    pattern = re.compile(r"class\s+(\w+)\s*\(.*(?:db\.Model|Base).*\)")
    for m in pattern.finditer(source):
        line_num = source.count("\n", 0, m.start()) + 1
        items.append({"line": line_num, "name": m.group(1)})
    # Also detect __tablename__ assignments
    for m in re.finditer(r"__tablename__\s*=\s*['\"](\w+)['\"]", source):
        line_num = source.count("\n", 0, m.start()) + 1
        items.append({"line": line_num, "tablename": m.group(1)})
    return items


def find_fstring_bugs(source: str) -> list[dict]:
    """Detect risky f-string patterns with dict access using same quotes."""
    items = []
    pattern = re.compile(r"""f(["'])[^"']*\{[^}]*\[['""][^"'"']*['""][^\}]*\}[^"']*\1""")
    for m in pattern.finditer(source):
        line_num = source.count("\n", 0, m.start()) + 1
        items.append({"line": line_num, "snippet": m.group(0)[:80]})
    # Specific known bug
    specific = re.compile(r"""f["']grades_\{cls\[['"]""")
    for m in specific.finditer(source):
        line_num = source.count("\n", 0, m.start()) + 1
        if not any(r["line"] == line_num for r in items):
            items.append({"line": line_num, "snippet": m.group(0)})
    return items


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Analyze routes and tables in app.py")
    parser.add_argument("--file", default="app.py", help="Path to app.py")
    args = parser.parse_args()

    app_path = Path(args.file)
    source = read_source(app_path)
    if source is None:
        sys.exit(1)

    print(f"Analyzing: {app_path.resolve()}")

    # Routes
    print_section("Routes")
    routes = find_routes(source)
    if routes:
        for r in routes:
            print(f"  Line {r['line']:4d}  [{r['methods']:20s}]  {r['path']}")
    else:
        print("  No routes found (check that app.py uses @app.route or @bp.route)")

    # CSRF exempt
    print_section("@csrf.exempt Decorators (security audit)")
    exempts = find_csrf_exempt(source)
    if exempts:
        for e in exempts:
            print(f"  Line {e['line']:4d}  function: {e['function']}")
            if "login" in e["function"].lower():
                print(f"          ⚠️  LOGIN route is exempt from CSRF — review this!")
    else:
        print("  None found ✓")

    # Limiter
    print_section("@limiter.limit Decorators")
    limits = find_limiter_limits(source)
    if limits:
        for lim in limits:
            print(f"  Line {lim['line']:4d}  {lim['decorator']}")
    else:
        print("  None found — add rate limiting to /login (see BRUTEFORCE_PROTECTION_SETUP.md)")

    # Models / Tables
    print_section("Database Models / Tables (SQLAlchemy)")
    models = find_models(source)
    if models:
        for m in models:
            if "name" in m:
                print(f"  Line {m['line']:4d}  class {m['name']} (db.Model)")
            else:
                print(f"  Line {m['line']:4d}  __tablename__ = {m['tablename']!r}")
    else:
        print("  No SQLAlchemy models found")

    # F-string bugs
    print_section("Potential f-string SyntaxError Patterns")
    bugs = find_fstring_bugs(source)
    if bugs:
        for b in bugs:
            print(f"  Line {b['line']:4d}  {b['snippet']!r}")
        print("\n  Suggested fix for download_name:")
        print("    name_part = cls['name'] if isinstance(cls, dict) and 'name' in cls else class_id")
        print("    download_name = f\"grades_{name_part}_{active_name}.pdf\".replace(' ', '_')")
    else:
        print("  No risky f-string patterns detected ✓")

    print("\n" + "=" * 60)
    print(f"  Total routes: {len(routes)}")
    print(f"  CSRF exempt:  {len(exempts)}")
    print(f"  Rate limits:  {len(limits)}")
    print(f"  Models:       {len([m for m in models if 'name' in m])}")
    print(f"  F-str bugs:   {len(bugs)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
