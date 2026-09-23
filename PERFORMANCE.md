# Low-end phone performance

The target is a responsive interface with bounded rendering work, including
when thousands of taxa are expanded. CPU throttling is a repeatable regression
test, not proof that every smartphone GPU or browser will behave identically.

## Enforced browser budgets

`node data/test_low_end_browser.cjs` runs all four pages in Chromium at a
360 × 740 viewport, device pixel ratio 2, touch input, and **8× CPU slowdown**.
It checks:

- At most **128 mounted tree rows** while navigating the expanded hierarchy.
- At most **2,500 page DOM elements** immediately after expand-all, before
  opening species details or mounting the deferred map.
- Expand-all's initial input handler returns in **under 100 ms**.
- No individual expand-all task exceeds **200 ms** at that slowdown; larger
  label sets must yield to the browser during preparation.
- **Zero web-font downloads** for the touch layout.
- End/Home reaches initially unmounted rows, one tab stop remains, newer
  actions cancel pending expansion, and search can reach the last species.

These thresholds cover the complete expand-all operation as well as bounded
DOM size. They do not claim that the complete operation finishes within one
frame. The previous tree remains displayed while a larger update is prepared;
the toolbar shows “Updating…” until the new layout is ready.

Example local runs for the bird page's 2,628-row expand-all operation at the
same viewport and 8× CPU slowdown:

| Measurement | Before this rework | After |
| --- | ---: | ---: |
| Page DOM elements after expansion | 22,059 | 1,595 |
| Initial button-handler time | 1,114 ms | 43 ms |
| Complete expansion, including paint | 2,639 ms | 750 ms |

The final run's longest individual expansion task was 129 ms. Results vary
with the host machine; the budget test is the repeatable acceptance check.

## Architecture

The tree keeps a logical row list and stable page height, but mounts SVG rows
in sections of 16 near the viewport. IntersectionObserver handles section
changes without a per-scroll layout loop. The current keyboard row stays
mounted; keyboard navigation and application search mount destinations before
focusing them. Browser text-find only sees currently mounted labels; use the
application search to find taxa anywhere in the full dataset.

Labels and search text are cached. Large preparation jobs and taxonomy/country
index construction yield in short batches. Touch layouts use installed system
fonts, avoid decorative overlays, and skip animated programmatic scrolling.
The map retains its selection and range data, with simpler paint during
movement and full hatching restored afterward. Deferred map space is reserved
before it enters the viewport.

Offline core assets and optional image packs retain their full contents but
use at most two simultaneous downloads. Failed core installation does not
activate the new worker and removes its incomplete cache.

## Verification

With the repository served on port 8000 and Playwright/Chromium available:

```text
node data/test_low_end_browser.cjs
node data/test_scroll_browser.cjs
node data/test_page_browser.cjs
node data/test_map_browser.cjs
node data/test_service_worker.cjs
node data/test_offline_browser.cjs
```

Set `PLAYWRIGHT_MODULE` to an external Playwright module directory if needed.
Build first for the offline browser test. The build and `data/smoke_test.py`
additionally verify generated pages and the offline asset list. Real-device
testing is still needed for GPU limitations,
memory pressure, browser-specific behavior, and thermal throttling.
