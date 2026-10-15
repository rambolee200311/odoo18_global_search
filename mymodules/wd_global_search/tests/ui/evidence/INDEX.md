# CC-018 Browser Evidence Index

The entry below records a captured run; it does not by itself close phase 1.
The phase remains open until the required verification and deviation review
are complete.

Add one row per captured run. Do not include usernames, cookies, raw search
queries, business values, authentication state, traces, or screenshots in this
tracked index. Runtime evidence belongs in this directory and is ignored.

| Test ID | Browser / version | Viewport | Fixture marker | Result | Evidence file |
|---|---|---|---|---|---|
| CC-TEST-023 | Chromium 116.0.5845.82 | Desktop 1440×900 | `CC018-2ceeda7c-97d6-4683-b565-01649a406c32` | PASS; navigation P95 21.427 ms, response-to-render P95 4.944 ms | `CC-TEST-023_chromium_desktop_20261015T074250Z.png`; `CC018-performance-chromium-20261015T074250Z.json` |
| CC-TEST-023 | Chromium 116.0.5845.82 | Desktop 1440×900 | `CC018-d1e3cd2e-20fb-42fa-9f84-68963be0dcb6` | PASS; navigation P95 22.639 ms (+5.7%), response-to-render P95 4.670 ms (-5.5%) vs phase 1 | `CC-TEST-023_chromium_desktop_20261015T083754Z.png`; `CC018-performance-chromium-20261015T083754Z.json` |
| CC-TEST-023 | Chromium 116.0.5845.82 | Desktop 1440×900 | `CC018-02252ea2-3ac3-472b-ac07-92c1b519da3e` | PASS; navigation P95 21.638 ms (+1.0%), response-to-render P95 4.882 ms (-1.3%) vs phase 1 | `CC-TEST-023_chromium_desktop_20261015T085931Z.png`; `CC018-performance-chromium-20261015T085931Z.json` |
