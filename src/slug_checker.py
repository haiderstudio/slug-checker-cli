#!/usr/bin/env python3
"""Check URL slugs are lowercase and clean, fail CI on a bad slug.

Run: python3 src/slug_checker.py examples/good-slugs.txt
     python3 src/slug_checker.py examples/bad-slugs.txt
     python3 src/slug_checker.py examples/posts/
     python3 src/slug_checker.py --slug my-new-post

The rule is one simple shape, applied to every slug found:

    lowercase letters a-z, digits 0-9, and hyphens only — no spaces,
    no uppercase, no underscores, no leading or trailing hyphen, and
    no double hyphen.

So `how-to-bake-sourdough` and `10-tips-for-better-sleep` pass, and
`My First Post` (uppercase and spaces), `my_first_post`
(underscore), `-leading-hyphen`, `trailing-hyphen-`,
`double--hyphen`, `café-guide` (bad character), and `my/post`
(bad character) all fail. Every problem is reported with its file
and line and a plain reason, and the tool exits 1 when any problem
is found — so it can fail a CI run — and 0 when every slug is clean.

Where slugs come from:

- A `.txt` file: one slug per line. Blank lines and `#` comment
  lines are skipped.
- A `.md` file: only the `slug:` line in the frontmatter is
  checked — the rest of the page is prose, not slugs.
- `--slug SLUG`: one slug given on the command line (repeatable).
- `--stdin`: one slug per line from standard input.
- A folder: every `.txt` and `.md` file under it, walked
  recursively unless `--no-recursive` is given. `.git` folders are
  never walked, and directory links are never followed.

It never rewrites a file. It is report-only and runs fully offline:
it sends nothing anywhere and needs no API key.

Exit codes: 0 when no problem is found, 1 when any problem is
found, 2 for a usage or input problem (a missing path, a bad flag,
no slugs to check).

Python standard library only.
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

VERSION = "1.0.0"

SLUG_KEY_RE = re.compile(r"^\s*slug\s*:\s*(.*)$", re.IGNORECASE)
ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")


def check_slug(slug):
    """Return the plain reasons a slug breaks the rule (empty = clean)."""
    if slug == "":
        return ["empty slug"]
    reasons = []
    upper = [c for c in slug if c.isupper()]
    if upper:
        reasons.append(f"uppercase letter '{upper[0]}'")
    if " " in slug:
        reasons.append("space in slug")
    if "_" in slug:
        reasons.append("underscore in slug")
    seen_bad = []
    for char in slug:
        if char not in ALLOWED and not char.isupper() and char not in (" ", "_"):
            if char not in seen_bad:
                seen_bad.append(char)
    for char in seen_bad:
        reasons.append(f"bad character '{char}'")
    if slug.startswith("-"):
        reasons.append("starts with a hyphen")
    if slug.endswith("-"):
        reasons.append("ends with a hyphen")
    if "--" in slug:
        reasons.append("double hyphen '--'")
    return reasons


def _strip_quotes(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def collect_from_file(path):
    """Return (slugs, problems) for one file.

    slugs is a list of (slug, line_number); problems is a list of
    (location, slug, reason) for files that cannot be read.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], [(str(path), "", "file is not valid UTF-8")]
    except OSError as exc:
        return [], [(str(path), "", f"cannot read file: {exc.strerror}")]
    slugs = []
    if path.suffix == ".md":
        for number, line in enumerate(text.splitlines(), start=1):
            match = SLUG_KEY_RE.match(line)
            if match:
                slugs.append((_strip_quotes(match.group(1)), number))
    else:
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                continue
            slugs.append((stripped, number))
    return slugs, []


def collect_from_text(text):
    """Collect one-slug-per-line slugs from stdin text."""
    slugs = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        slugs.append((stripped, number))
    return slugs


def gather(paths, exclude, recursive):
    """Walk the given paths and return (entries, file_problems).

    entries is a list of (location, slug, line_number); file_problems
    is a list of (location, slug, reason) for unreadable files.
    """
    entries = []
    file_problems = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(raw)
        if path.is_file():
            slugs, problems = collect_from_file(path)
            file_problems.extend(problems)
            for slug, number in slugs:
                entries.append((f"{path}:{number}", slug, number))
            continue
        if recursive:
            for dirpath, dirnames, filenames in _walk(path):
                for name in filenames:
                    candidate = Path(dirpath) / name
                    if candidate.suffix not in (".txt", ".md"):
                        continue
                    if _excluded(candidate, path, exclude):
                        continue
                    slugs, problems = collect_from_file(candidate)
                    file_problems.extend(problems)
                    for slug, number in slugs:
                        entries.append((f"{candidate}:{number}", slug, number))
        else:
            for candidate in sorted(path.iterdir()):
                if not candidate.is_file():
                    continue
                if candidate.suffix not in (".txt", ".md"):
                    continue
                if _excluded(candidate, path, exclude):
                    continue
                slugs, problems = collect_from_file(candidate)
                file_problems.extend(problems)
                for slug, number in slugs:
                    entries.append((f"{candidate}:{number}", slug, number))
    return entries, file_problems


def _walk(root):
    """os.walk that never enters .git and never follows links."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        yield dirpath, dirnames, filenames


def _excluded(candidate, root, patterns):
    name = candidate.name
    try:
        rel = str(candidate.relative_to(root))
    except ValueError:
        rel = name
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern)
        for pattern in patterns
    )


def check_entries(entries):
    """Turn (location, slug, line) entries into (location, slug, reason)."""
    problems = []
    for location, slug, _number in entries:
        for reason in check_slug(slug):
            problems.append((location, slug, reason))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="slug-checker-cli",
        description="Check URL slugs are lowercase and clean.",
    )
    parser.add_argument("paths", nargs="*", help="files or folders to check")
    parser.add_argument(
        "--slug",
        dest="slugs",
        action="append",
        default=[],
        metavar="SLUG",
        help="check one slug given on the command line (repeatable)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read one slug per line from standard input",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="skip files matching this glob (repeatable)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not walk into subfolders",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as JSON (summary goes to stderr)",
    )
    parser.add_argument("--version", action="store_true", help="print the version")
    args = parser.parse_args(argv)

    if args.version:
        print(f"slug-checker-cli {VERSION}")
        return 0

    entries = []
    file_problems = []
    try:
        if args.paths:
            found, file_problems = gather(
                args.paths, args.exclude, not args.no_recursive
            )
            entries.extend(found)
    except FileNotFoundError as exc:
        print(f"error: no such file or folder: {exc}", file=sys.stderr)
        return 2

    for slug in args.slugs:
        entries.append(("<command line>", slug, 0))
    if args.stdin:
        for slug, number in collect_from_text(sys.stdin.read()):
            entries.append((f"<stdin>:{number}", slug, number))

    if not entries and not file_problems:
        print("error: no slugs to check", file=sys.stderr)
        return 2

    problems = check_entries(entries)
    problems.extend(file_problems)
    checked = len(entries)
    bad_slugs = len({location for location, _slug, _r in problems if _slug != ""})
    total_problems = len(problems)

    if args.json:
        result = {
            "slugs": [
                {
                    "location": location,
                    "slug": slug,
                    "problems": [
                        reason
                        for loc, _s, reason in problems
                        if loc == location
                    ],
                }
                for location, slug, _number in entries
            ],
            "summary": {
                "checked": checked,
                "ok": checked - bad_slugs,
                "failed": bad_slugs,
                "problems": total_problems,
            },
        }
        print(json.dumps(result, indent=2))
        if problems:
            print(
                f"Checked {checked} slug(s), {total_problems} problem(s) "
                f"in {bad_slugs} slug(s).",
                file=sys.stderr,
            )
        else:
            print(
                f"OK — {checked} slug(s) checked, all slugs are clean.",
                file=sys.stderr,
            )
        return 1 if problems else 0

    if not entries and file_problems:
        for location, _slug, reason in file_problems:
            print(f"FAIL {location}: {reason}")
        print(
            f"Checked 0 slug(s), {total_problems} problem(s) in 0 slug(s)."
        )
        return 1

    for location, slug, reason in problems:
        if slug:
            print(f"FAIL {location}: '{slug}': {reason}")
        else:
            print(f"FAIL {location}: {reason}")
    if problems:
        print(
            f"Checked {checked} slug(s), {total_problems} problem(s) "
            f"in {bad_slugs} slug(s)."
        )
        return 1
    print(f"OK — {checked} slug(s) checked, all slugs are clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
