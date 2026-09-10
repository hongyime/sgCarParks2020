# Decisions

- 2026-09-11: Reproduce failures with a synthetic CSV before changing the application. Preserve the tracked CSV and target the verified default/Pages branch, master; the divergent main branch is not the maintenance base.
- 2026-09-11: The existing Pages URL serves a README and the legacy Heroku URL returns 404. Restore real search on Pages using the shared template plus a derived static catalog, and retain the repaired Flask interface. This introduces no Vercel/Supabase usage and preserves all source data.
- 2026-09-11: PR verification exposed a legacy Labeler configuration path that does not exist. Use the repository's existing labels.yml and explicit label-write permissions; retain the workflow and its history.
- 2026-09-11: PR #113 is merged and the exact Pages release c6291ff is browser/byte verified. Preserve the original CSV and both branch histories. Flask production hosting, a possible Supabase data migration, and shared workflow hygiene remain explicit follow-ups.
