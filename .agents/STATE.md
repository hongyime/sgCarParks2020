# Current work

2026-09-11: Repair the nearest-carpark application under the accepted portfolio upkeep plan.

- Work is based on verified default/Pages branch `master` at `5f6bde8994faa8d6872c67c56b1648f401f90480`. Origin/main has divergent history and is not the maintenance base.
- Fixed double CSV loading, naive comma splitting, global search mutation, quadratic nearest lookup, invalid-coordinate HTTP 500s and absent page templates. Source CSV remains byte-for-byte unchanged (2,137 unique records).
- Added a working static companion for the existing GitHub Pages master/root deployment, built from the shared Flask template and preserved CSV. One lazy catalog download, no polling or cloud API calls, 10-second/1 MiB download bounds, recoverable errors, keyboard support and Prawn Projects styling.
- Flask remains supported without JavaScript. Removed unused login/websocket runtime dependencies and switched the Procfile to a normal threaded Gunicorn worker. The old Heroku URL returns 404; separate hosted Flask runtime remains unverified.
- Local synthetic Python/API tests pass (18; Unix WSGI test reserved for Linux CI), and 12 browser-logic tests pass. Ten browser scenarios pass across desktop/390px/320px, keyboard navigation, one download across repeated searches, deep links/back navigation, retries, stale-result prevention, HTML escaping, and no-JavaScript guidance/Flask use. All nine installed runtime packages have no known vulnerabilities in the dependency audit. Publication and exact live asset verification are still pending.
- Remaining steps: finish browser/audit checks, inspect changes, publish to master without rewriting history, verify Linux CI/Pages and public search, update portfolio evidence at https://aoo181uudk96.postplan.dev.
