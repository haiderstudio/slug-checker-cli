#!/bin/sh
# Run the checker on the bundled examples.
# Run from the repo root: sh examples/run-example.sh
# The bad-slugs run exits 1 because every slug in it breaks the
# slug rule on purpose — that is the expected result here.
set -e
cd "$(dirname "$0")/.."
echo "--- check the good slugs ---"
python3 src/slug_checker.py examples/good-slugs.txt
echo "--- check the bad slugs ---"
python3 src/slug_checker.py examples/bad-slugs.txt || true
echo "--- check the posts ---"
python3 src/slug_checker.py examples/posts/ || true
