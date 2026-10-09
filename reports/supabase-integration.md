# Supabase integration verification

2026-10-09: connected to PlacidWay Knowledge Assistant, project nakfsvmzgcroxbfuokpd, Gabriel-Kelvin's Org, Free plan. No paid resources or deployment were enabled.

30/30 local tests passed, including privacy, pre-connection backfill, failure/retry and project-specific snapshot tracking.

Live checks passed:
- Three application tables have RLS enabled and no anon/authenticated grants; server-role access works.
- Anonymous REST reads on all tables and an anonymous write were denied.
- Initial sync uploaded 28 topic records and one snapshot containing all seven pages; pending queue reached zero. No raw question/answer transcripts were uploaded.
- A synthetic lead was encrypted, synced, decrypted successfully by the backend, then removed from both cloud and local cache. No real leads existed at verification time.
- The running health endpoint and protected admin dashboard/manual sync report success. The background worker retries every minute.
- Public execution of Supabase's auto-RLS event-trigger helper was revoked. Security advisors now have no WARN/ERROR findings.

Advisor informational findings: RLS-without-policies is intentional for these server-only tables; no public access is allowed. See https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy . Fresh retention indexes were reported unused before enough traffic; keep them for timestamp-based cleanup. See https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index .

Limits: the admin dashboard reads its local cache; it does not restore cloud data automatically after losing that cache. Keep the lead-encryption key backed up privately. Cleanup and retries run while the app is running. Production authentication, shared rate limits, database-native retention, backups/restore and seven-day uptime verification remain deployment work.

Secrets stay in the server environment and are excluded from the submission archive. The database password is not needed for the REST backend connection.
