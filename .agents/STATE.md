# Current status

2026-09-16: wave-2b baseline review complete. No open PRs, no secrets. Repo healthy.

Prior state (2026-09-11): PR #113 merged — nearest-carpark search on Pages restored. Public app https://hongyime.github.io/sgCarParks2020/ verified. 2,137 CSV records preserved (SHA-256 affba0887ff35fcd471a5d5996468dcedf91e806afa282638987165c8a583939). 19 Python tests + 12 Node tests passed. master is the default/Pages branch; main is divergent (do not merge).

Open follow-ups (from 2026-09-11):
- Flask production hosting unverified (old Heroku URL 404)
- Supabase data migration still potential future work
- Shared workflow/action-tag hygiene warnings remain

## Privacy maintenance - 2026-09-27

Remove the optional personal security contact while retaining private vulnerability-reporting guidance. The narrow documentation patch is prepared from the current default branch; staged whitespace and the inherited identity hook are publication checks. Application behavior is unchanged.
