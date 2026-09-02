#!/bin/sh
# Build the published site into public/.
#
# The pages are served from GitLab Pages with access control on, where a
# fetch() for a data file can be bounced to the cross-origin sign-in flow and
# fail CORS even though the page itself loaded. So the data is bundled into the
# HTML here: every line reading "INLINE <path>" is replaced by that file's
# contents, filling the <script type="application/json"> blocks at the end of
# each page.
set -eu

bundle() {
  awk '/^INLINE /{f=$2; while((getline l < f) > 0) print l; close(f); next} {print}' "$1" > "$2"
}

rm -rf public
mkdir public
bundle chiroptera-tree.html public/index.html
bundle marine-mammal-tree.html public/marine.html

for f in public/index.html public/marine.html; do
  grep -q '^INLINE ' "$f" && { echo "$f: data was not inlined" >&2; exit 1; }
  grep -q '"speciesCount"' "$f" || { echo "$f: taxonomy missing" >&2; exit 1; }
done
echo "built: $(ls -l public | tail -n +2 | wc -l) files"
