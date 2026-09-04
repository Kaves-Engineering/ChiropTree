#!/bin/sh
# Build the published site into public/.
#
# Build the static GitHub Pages site. Data stays as separate files so browsers
# can parse the interface before loading the taxonomy and cache it separately.
set -eu

uv run data/build_marine_mammal_page.py

rm -rf public
mkdir -p public/data/images
cp chiroptera-tree.html public/index.html
cp marine-mammal-tree.html public/marine.html
cp data/*.json public/data/
cp manifest.webmanifest public/
if [ -d data/images ]; then cp -R data/images/. public/data/images/; fi

release=$(sha256sum public/index.html public/marine.html public/data/*.json | sha256sum | cut -c1-16)
sed "s/__RELEASE__/$release/" service-worker.js > public/service-worker.js

for f in public/index.html public/marine.html; do
  grep -q "data/.*taxonomy.json" "$f" || { echo "$f: taxonomy URL missing" >&2; exit 1; }
done
grep -q '__RELEASE__' public/service-worker.js && { echo "service worker release missing" >&2; exit 1; }
echo "built: $(ls -l public | tail -n +2 | wc -l) files"
