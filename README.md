# slug-checker-cli

Check URL slugs are lowercase and clean, fail CI on a bad slug.

[![CI](https://github.com/haiderstudio/slug-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/slug-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`slug_checker` reads the slugs you give it and checks every one
against one simple rule:

- lowercase letters a-z, digits 0-9, and hyphens only: no spaces,
  no uppercase, no underscores, no leading or trailing hyphen, no
  double hyphen

So `how-to-bake-sourdough` and `10-tips-for-better-sleep` pass,
and `My First Post` (uppercase and spaces), `my_first_post`
(underscore), `-leading-hyphen` (leading hyphen),
`trailing-hyphen-` (trailing hyphen), `double--hyphen` (double
hyphen), `café-guide` (bad character), and `my/post` (bad
character) all fail. Each problem is reported with its file and
line and a plain reason, and the tool exits 1 when any problem is
found — so it can fail a CI run. A clean list exits 0.

- A slug can carry more than one reason: `My First Post` is
  reported once for the uppercase letter and once for the space,
  so the fix is clear. A bad character shared by one slug is
  reported once.
- Slugs come from three places: a `.txt` file (one slug per line),
  a `.md` file (only the `slug:` line in the frontmatter is
  checked — the rest of the page is prose, not slugs), or
  `--slug SLUG` on the command line (repeatable), or `--stdin`
  (one slug per line). Blank lines and `#` comment lines in a
  `.txt` file are skipped.
- Folders are walked recursively by default (`--no-recursive`
  stops at the top level). Only `.txt` and `.md` files are picked
  up in a folder walk. `.git` folders are never walked, and
  directory links are never followed, so a link cycle cannot loop
  the check.
- `--exclude PATTERN` skips files by glob, for example
  `--exclude 'draft-*'`. It can be repeated.
- `--json` prints the result as machine-readable JSON (the
  summary goes to standard error, so standard output stays
  clean JSON).
- It is report-only and runs fully offline: it never rewrites a
  file, sends nothing anywhere, and needs no API key.

## What it does NOT do

- It does not rename pages or rewrite slugs. A bad slug is
  reported; fixing it is your job.
- It does not check that a slug is unique — only that its shape
  is clean. Two pages can share a clean slug and this tool stays
  quiet.
- It does not check that a slug matches the page title, or that
  the page exists. Slug shape only.
- It does not fetch anything. Every input is a local file, a
  command-line slug, or standard input.

## Who it is for

Anyone who publishes pages and wants clean URLs: a blogger
checking a list of slugs before posting, a docs writer keeping
page slugs tidy, or anyone adding a CI step that fails the build
on a bad slug. A bad slug hurts search ranking and looks
unprofessional in a shared link — this catches it before the page
goes live.

## How this differs from similar tools

URL slug checkers barely exist as tools. The exact name
`slug-checker-cli` matches 0 repositories on GitHub (checked
Nov 8, 2026), and `url slug checker cli` matches 0 too. The
wider field is different jobs wearing the same words:
yutaka-art/slug-checker (0 stars) checks whether a GitHub
username is free, m2mahdavi/unique-slug-checker (0 stars) checks
WordPress slug uniqueness, and saumitrob-commits/slugcheck
(0 stars) checks skincare for the "slugging" trend. The closest
thing to validation is webfactory/slug-validation-bundle
(6 stars), which validates slugs inside Symfony apps — a
framework check, not a local file checker. The biggest name in
`slug validator` results, nette/utils (2,147 stars), is a general
string-utility library, not a slug tool at all. None of them
checks URL slug shape in local files and fails CI on a bad one.
This tool does that one job: a Python standard-library-only CLI
that reads slugs from files, frontmatter, or the command line,
reports every problem with a file and line, and exits 1 on a bad
slug — no install beyond Python, no website, no network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/slug-checker-cli.git
cd slug-checker-cli
python3 src/slug_checker.py examples/good-slugs.txt
```

```
OK — 5 slug(s) checked, all slugs are clean.
```

## Usage

Check one file:

```
python3 src/slug_checker.py examples/good-slugs.txt
```

Check several files at once:

```
python3 src/slug_checker.py examples/good-slugs.txt examples/bad-slugs.txt
```

```
FAIL examples/bad-slugs.txt:1: 'My First Post': uppercase letter 'M'
FAIL examples/bad-slugs.txt:1: 'My First Post': space in slug
FAIL examples/bad-slugs.txt:2: 'my_first_post': underscore in slug
FAIL examples/bad-slugs.txt:3: '-leading-hyphen': starts with a hyphen
FAIL examples/bad-slugs.txt:4: 'trailing-hyphen-': ends with a hyphen
FAIL examples/bad-slugs.txt:5: 'double--hyphen': double hyphen '--'
FAIL examples/bad-slugs.txt:6: 'café-guide': bad character 'é'
FAIL examples/bad-slugs.txt:7: 'my/post': bad character '/'
FAIL examples/bad-slugs.txt:8: 'UPPERCASE': uppercase letter 'U'
Checked 8 slug(s), 9 problem(s) in 8 slug(s).
```

Check a whole folder:

```
python3 src/slug_checker.py examples/
```

```
FAIL examples/bad-slugs.txt:1: 'My First Post': uppercase letter 'M'
FAIL examples/bad-slugs.txt:1: 'My First Post': space in slug
FAIL examples/bad-slugs.txt:2: 'my_first_post': underscore in slug
FAIL examples/bad-slugs.txt:3: '-leading-hyphen': starts with a hyphen
FAIL examples/bad-slugs.txt:4: 'trailing-hyphen-': ends with a hyphen
FAIL examples/bad-slugs.txt:5: 'double--hyphen': double hyphen '--'
FAIL examples/bad-slugs.txt:6: 'café-guide': bad character 'é'
FAIL examples/bad-slugs.txt:7: 'my/post': bad character '/'
FAIL examples/bad-slugs.txt:8: 'UPPERCASE': uppercase letter 'U'
FAIL examples/posts/bad-post.md:3: 'My First Post': uppercase letter 'M'
FAIL examples/posts/bad-post.md:3: 'My First Post': space in slug
Checked 15 slug(s), 11 problem(s) in 9 slug(s).
```

Check slugs given on the command line:

```
python3 src/slug_checker.py --slug my-new-post --slug "My Bad Slug"
```

```
FAIL <command line>: 'My Bad Slug': uppercase letter 'M'
FAIL <command line>: 'My Bad Slug': space in slug
Checked 2 slug(s), 2 problem(s) in 1 slug(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output stays clean JSON):

```
python3 src/slug_checker.py examples/good-slugs.txt --json
```

```
{
  "slugs": [
    {
      "location": "examples/good-slugs.txt:1",
      "slug": "how-to-bake-sourdough",
      "problems": []
    },
    {
      "location": "examples/good-slugs.txt:2",
      "slug": "best-cheap-protein-meals",
      "problems": []
    },
    {
      "location": "examples/good-slugs.txt:3",
      "slug": "vcloud-vs-other-isps-2026",
      "problems": []
    },
    {
      "location": "examples/good-slugs.txt:4",
      "slug": "10-tips-for-better-sleep",
      "problems": []
    },
    {
      "location": "examples/good-slugs.txt:5",
      "slug": "a",
      "problems": []
    }
  ],
  "summary": {
    "checked": 5,
    "ok": 5,
    "failed": 0,
    "problems": 0
  }
}
```

Exit codes: 0 when every slug is clean, 1 when any slug has a
problem, 2 for a usage problem (no slugs given, a bad flag, a
missing file or folder).

## Examples

### 1. A bad list — nine problems in eight slugs

`examples/bad-slugs.txt` has one of each slug fault:

```
python3 src/slug_checker.py examples/bad-slugs.txt
```

```
FAIL examples/bad-slugs.txt:1: 'My First Post': uppercase letter 'M'
FAIL examples/bad-slugs.txt:1: 'My First Post': space in slug
FAIL examples/bad-slugs.txt:2: 'my_first_post': underscore in slug
FAIL examples/bad-slugs.txt:3: '-leading-hyphen': starts with a hyphen
FAIL examples/bad-slugs.txt:4: 'trailing-hyphen-': ends with a hyphen
FAIL examples/bad-slugs.txt:5: 'double--hyphen': double hyphen '--'
FAIL examples/bad-slugs.txt:6: 'café-guide': bad character 'é'
FAIL examples/bad-slugs.txt:7: 'my/post': bad character '/'
FAIL examples/bad-slugs.txt:8: 'UPPERCASE': uppercase letter 'U'
Checked 8 slug(s), 9 problem(s) in 8 slug(s).
```

### 2. A blog post's frontmatter slug

`examples/posts/bad-post.md` carries its slug in the frontmatter,
and only that line is checked — the title and body are left alone:

```
python3 src/slug_checker.py examples/posts/
```

```
FAIL examples/posts/bad-post.md:3: 'My First Post': uppercase letter 'M'
FAIL examples/posts/bad-post.md:3: 'My First Post': space in slug
Checked 2 slug(s), 2 problem(s) in 1 slug(s).
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the good slugs (pass), then the bad slugs
(fail, on purpose), then the posts (fail, on purpose). Its full
output is in `examples/sample-output.md`, ending with
`Checked 2 slug(s), 2 problem(s) in 1 slug(s).` The bad-slugs
and posts runs exit 1, which is the expected result — the script
ends with exit 0 so it can be run as a demo.

## How it is tested

46 tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_slug_checker.py
```

The tests cover: every slug fault (uppercase, space, underscore,
leading and trailing hyphen, double hyphen, bad character,
non-ASCII letter, empty slug, one slug with two reasons, each
bad character reported once), clean slugs, `.txt` parsing
(blank lines and comments skipped, line numbers),
`.md` frontmatter parsing (only `slug:` lines checked, quoted
values, empty value, no slug line), folder walking (recursive,
`--no-recursive`, `.git` skipped, `--exclude`, non-slug files
skipped), the CLI (exit 0/1/2, `--slug`, `--stdin`, `--json`
output, `--version`, bad flags, missing paths, empty folders,
input files left unchanged), the bundled examples (sample output
compared byte-for-byte against a fresh run, and the
README-quoted outputs checked against it), and hygiene checks
(no placeholder text, no absolute paths, stdlib imports only,
`.env` first in `.gitignore`).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea of
checking URL slugs is not new — the similar tools named above
(the username-availability checker, the WordPress uniqueness
checker, the Symfony validation bundle) are listed in "How this
differs" — but every line of code here is original, and the tool
builds on nothing but Python's standard library.
