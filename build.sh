#!/bin/sh
# Build the published site into public/.
#
# Build the static GitHub Pages site. Data stays as separate files so browsers
# can parse the interface before loading the taxonomy and cache it separately.
set -eu

uv run data/build_marine_mammal_page.py
uv run data/build_bird_page.py
uv run data/build_dinosaur_page.py

rm -rf public
mkdir -p public/data/images
cp chiroptera-tree.html public/index.html
cp marine-mammal-tree.html public/marine.html
cp bird-tree.html public/birds.html
cp dinosaur-tree.html public/dinosaurs.html
cp data/*.json public/data/
# already merged into bird_taxonomy.json; no page loads it
rm -f public/data/bird_gbif_countries.json
# The call export lives in a subdirectory, so the glob above misses it.
mkdir -p public/data/calls/exports
cp data/calls/exports/calls.json public/data/calls/exports/
cp manifest.webmanifest public/
if [ -d data/images ]; then cp -R data/images/. public/data/images/; fi

release=$(sha256sum public/index.html public/marine.html public/birds.html public/dinosaurs.html public/data/*.json | sha256sum | cut -c1-16)
sed "s/__RELEASE__/$release/" service-worker.js > public/service-worker.js

for f in public/index.html public/marine.html public/birds.html public/dinosaurs.html; do
  grep -q "data/.*taxonomy.json" "$f" || { echo "$f: taxonomy URL missing" >&2; exit 1; }
done
grep -q '__RELEASE__' public/service-worker.js && { echo "service worker release missing" >&2; exit 1; }
echo "built: $(ls -l public | tail -n +2 | wc -l) files"
