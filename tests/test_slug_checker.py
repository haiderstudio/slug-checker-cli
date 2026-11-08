"""Tests for slug_checker — standard library unittest only."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(SRC))

import slug_checker  # noqa: E402


def run_cli(*args, cwd=None, stdin=None):
    argv = [sys.executable, str(SRC / "slug_checker.py"), *args]
    return subprocess.run(
        argv, capture_output=True, text=True, cwd=cwd or ROOT, input=stdin
    )


def write(tmp, name, text="content\n"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class CheckSlugTests(unittest.TestCase):
    def check(self, slug):
        return slug_checker.check_slug(slug)

    def test_clean_slugs(self):
        for slug in (
            "how-to-bake-sourdough",
            "best-cheap-protein-meals",
            "vcloud-vs-other-isps-2026",
            "10-tips-for-better-sleep",
            "a",
            "1",
            "a1-b2",
        ):
            with self.subTest(slug=slug):
                self.assertEqual(self.check(slug), [])

    def test_empty_slug(self):
        self.assertEqual(self.check(""), ["empty slug"])

    def test_uppercase_letter(self):
        reasons = self.check("My First Post")
        self.assertIn("uppercase letter 'M'", reasons)
        self.assertIn("uppercase letter 'U'", self.check("UPPERCASE"))

    def test_space_in_slug(self):
        self.assertIn("space in slug", self.check("My First Post"))

    def test_underscore_in_slug(self):
        self.assertIn("underscore in slug", self.check("my_first_post"))

    def test_leading_hyphen(self):
        self.assertIn("starts with a hyphen", self.check("-leading-hyphen"))

    def test_trailing_hyphen(self):
        self.assertIn("ends with a hyphen", self.check("trailing-hyphen-"))

    def test_double_hyphen(self):
        self.assertIn("double hyphen '--'", self.check("double--hyphen"))

    def test_bad_character(self):
        self.assertIn("bad character '@'", self.check("weird@name"))
        self.assertIn("bad character '/'", self.check("my/post"))
        self.assertIn("bad character '.'", self.check("my.post"))

    def test_non_ascii_letter_is_bad_character(self):
        self.assertIn("bad character 'é'", self.check("café-guide"))

    def test_one_slug_can_carry_two_reasons(self):
        reasons = self.check("My First Post")
        self.assertIn("uppercase letter 'M'", reasons)
        self.assertIn("space in slug", reasons)
        self.assertEqual(len(reasons), 2)

    def test_each_bad_character_reported_once(self):
        reasons = self.check("a@b@c")
        self.assertEqual(
            [r for r in reasons if r.startswith("bad character")],
            ["bad character '@'"],
        )


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_txt_file_skips_blanks_and_comments(self):
        path = write(
            self.tmp.name,
            "slugs.txt",
            "\n# a comment\n\nmy-post\n\n  spaced-slug  \n",
        )
        slugs, problems = slug_checker.collect_from_file(path)
        self.assertEqual(problems, [])
        self.assertEqual(slugs, [("my-post", 4), ("spaced-slug", 6)])

    def test_txt_line_numbers(self):
        path = write(
            self.tmp.name, "slugs.txt", "good-one\nMy Bad\nanother-good\n"
        )
        slugs, _ = slug_checker.collect_from_file(path)
        self.assertEqual(
            slugs, [("good-one", 1), ("My Bad", 2), ("another-good", 3)]
        )

    def test_md_file_checks_only_slug_lines(self):
        path = write(
            self.tmp.name,
            "post.md",
            "---\ntitle: My First Post\nslug: my-first-post\n"
            "date: 2026-11-08\n---\n\nSome body text with CAPS and spaces.\n",
        )
        slugs, problems = slug_checker.collect_from_file(path)
        self.assertEqual(problems, [])
        self.assertEqual(slugs, [("my-first-post", 3)])

    def test_md_file_quoted_slug_value(self):
        path = write(
            self.tmp.name, "post.md", '---\nslug: "my-first-post"\n---\n'
        )
        slugs, _ = slug_checker.collect_from_file(path)
        self.assertEqual(slugs, [("my-first-post", 2)])

    def test_md_file_empty_slug_value(self):
        path = write(self.tmp.name, "post.md", "---\nslug:\n---\n")
        slugs, _ = slug_checker.collect_from_file(path)
        self.assertEqual(slugs, [("", 2)])
        self.assertEqual(slug_checker.check_slug(slugs[0][0]), ["empty slug"])

    def test_md_file_without_slug_line(self):
        path = write(
            self.tmp.name, "post.md", "---\ntitle: No Slug Here\n---\n"
        )
        slugs, _ = slug_checker.collect_from_file(path)
        self.assertEqual(slugs, [])

    def test_non_utf8_file_is_a_problem(self):
        path = Path(self.tmp.name) / "bad.txt"
        path.write_bytes(b"good-one\n\xff\xfe\n")
        slugs, problems = slug_checker.collect_from_file(path)
        self.assertEqual(slugs, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("not valid UTF-8", problems[0][2])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            slug_checker.gather(
                [str(Path(self.tmp.name) / "nope.txt")], [], True
            )


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_clean_file_exits_zero(self):
        path = write(self.tmp.name, "good.txt", "my-post\nanother-post\n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "OK — 2 slug(s) checked, all slugs are clean.", result.stdout
        )

    def test_bad_file_exits_one_with_line_numbers(self):
        path = write(self.tmp.name, "bad.txt", "good-one\nMy Bad\n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"FAIL {path}:2: 'My Bad': uppercase letter 'M'",
                      result.stdout)
        self.assertIn(f"FAIL {path}:2: 'My Bad': space in slug",
                      result.stdout)
        self.assertIn(
            "Checked 2 slug(s), 2 problem(s) in 1 slug(s).", result.stdout
        )

    def test_slug_flag(self):
        result = run_cli("--slug", "my-post", "--slug", "My Bad")
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "FAIL <command line>: 'My Bad': uppercase letter 'M'",
            result.stdout,
        )

    def test_slug_flag_clean_only(self):
        result = run_cli("--slug", "my-post")
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "OK — 1 slug(s) checked, all slugs are clean.", result.stdout
        )

    def test_stdin(self):
        result = run_cli("--stdin", stdin="my-post\nmy_bad\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL <stdin>:2: 'my_bad': underscore in slug",
                      result.stdout)

    def test_json_output_parses(self):
        path = write(self.tmp.name, "bad.txt", "good-one\nMy Bad\n")
        result = run_cli(str(path), "--json")
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["summary"]["checked"], 2)
        self.assertEqual(data["summary"]["problems"], 2)
        self.assertEqual(data["summary"]["failed"], 1)
        self.assertIn("Checked 2 slug(s)", result.stderr)

    def test_json_clean(self):
        path = write(self.tmp.name, "good.txt", "my-post\n")
        result = run_cli(str(path), "--json")
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["summary"]["problems"], 0)
        self.assertIn("all slugs are clean", result.stderr)

    def test_version(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("slug-checker-cli", result.stdout)

    def test_missing_path_exits_two(self):
        result = run_cli(str(Path(self.tmp.name) / "nope.txt"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("no such file or folder", result.stderr)

    def test_no_input_exits_two(self):
        result = run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no slugs to check", result.stderr)

    def test_empty_folder_exits_two(self):
        result = run_cli(self.tmp.name)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no slugs to check", result.stderr)

    def test_bad_flag_exits_two(self):
        result = run_cli("--nope")
        self.assertEqual(result.returncode, 2)

    def test_folder_walk(self):
        write(self.tmp.name, "good.txt", "my-post\n")
        write(self.tmp.name, "sub/bad.txt", "My Bad\n")
        write(self.tmp.name, "sub/notes.csv", "My Bad\n")
        result = run_cli(self.tmp.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Checked 2 slug(s), 2 problem(s) in 1 slug(s).", result.stdout
        )

    def test_no_recursive(self):
        write(self.tmp.name, "good.txt", "my-post\n")
        write(self.tmp.name, "sub/bad.txt", "My Bad\n")
        result = run_cli(self.tmp.name, "--no-recursive")
        self.assertEqual(result.returncode, 0)

    def test_git_folder_skipped(self):
        write(self.tmp.name, ".git/hooks/bad.txt", "My Bad\n")
        write(self.tmp.name, "good.txt", "my-post\n")
        result = run_cli(self.tmp.name)
        self.assertEqual(result.returncode, 0)

    def test_exclude(self):
        write(self.tmp.name, "good.txt", "my-post\n")
        write(self.tmp.name, "skip.txt", "My Bad\n")
        result = run_cli(self.tmp.name, "--exclude", "skip.txt")
        self.assertEqual(result.returncode, 0)

    def test_md_folder_walk_checks_frontmatter_only(self):
        write(
            self.tmp.name,
            "post.md",
            "---\ntitle: My Bad Title\nslug: my-post\n---\n\nBody.\n",
        )
        result = run_cli(self.tmp.name)
        self.assertEqual(result.returncode, 0)

    def test_input_files_unchanged(self):
        path = write(self.tmp.name, "slugs.txt", "my-post\nMy Bad\n")
        before = path.read_text()
        run_cli(str(path))
        self.assertEqual(path.read_text(), before)

    def test_bundled_examples(self):
        clean = run_cli("examples/good-slugs.txt")
        self.assertEqual(clean.returncode, 0)
        self.assertIn(
            "OK — 5 slug(s) checked, all slugs are clean.", clean.stdout
        )
        bad = run_cli("examples/bad-slugs.txt")
        self.assertEqual(bad.returncode, 1)
        self.assertIn(
            "Checked 8 slug(s), 9 problem(s) in 8 slug(s).", bad.stdout
        )
        posts = run_cli("examples/posts/")
        self.assertEqual(posts.returncode, 1)
        self.assertIn(
            "Checked 2 slug(s), 2 problem(s) in 1 slug(s).", posts.stdout
        )
        whole = run_cli("examples/")
        self.assertEqual(whole.returncode, 1)
        self.assertIn(
            "Checked 15 slug(s), 11 problem(s) in 9 slug(s).", whole.stdout
        )

    def test_sample_output_matches_a_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout, (EXAMPLES / "sample-output.md").read_text()
        )

    def test_run_example_script_exits_zero(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)


class HygieneTests(unittest.TestCase):
    """The template gate: no placeholder text, no secrets, no local
    paths, stdlib imports only. The scan skips .git and __pycache__
    (Day 21 rule) and skips tests/ itself (Day 22 pattern), because
    this file's own banned-word list would otherwise trip it."""

    BANNED = ("TODO", "FIXME", "coming soon", "lorem", "API_KEY")

    def _repo_files(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts:
                continue
            yield path

    def test_no_placeholder_text(self):
        hits = []
        for path in self._repo_files():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for word in self.BANNED:
                if word in text:
                    hits.append(f"{path.relative_to(ROOT)}: {word}")
        self.assertEqual(hits, [])

    def test_no_absolute_local_paths(self):
        hits = []
        for path in self._repo_files():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "/home/" in text or "/Users/" in text or "C:\\" in text:
                hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [])

    def test_stdlib_only_imports(self):
        import ast

        allowed = {
            "argparse",
            "fnmatch",
            "json",
            "os",
            "re",
            "sys",
            "pathlib",
            # Test file only: json, subprocess, tempfile, unittest.
            "subprocess",
            "tempfile",
            "unittest",
        }
        src = ROOT / "src" / "slug_checker.py"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        self.assertEqual(imported - allowed, set())

    def test_gitignore_lists_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_readme_quoted_outputs_are_real(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn(
            "FAIL examples/bad-slugs.txt:1: 'My First Post': "
            "uppercase letter 'M'",
            readme,
        )
        self.assertIn(
            "Checked 8 slug(s), 9 problem(s) in 8 slug(s).", readme
        )
        self.assertIn(
            "OK — 5 slug(s) checked, all slugs are clean.", readme
        )


if __name__ == "__main__":
    unittest.main()
