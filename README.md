# PlacidWay Care Navigator

Live demo: https://placidway-care-navigator.onrender.com · Admin: https://placidway-care-navigator.onrender.com/admin

An assessment chatbot grounded in the seven PlacidWay pages supplied in the assessment. It provides exact source excerpts, package-aware price answers, clear refusals, a source inspector, a protected operations dashboard, and repeatable evaluations.

**Deployment:** one Free Render Python web service, with Supabase as the persistent backend. This is an assessment prototype, not an official PlacidWay service. Free hosting may sleep when idle; seven-day uninterrupted uptime is not guaranteed.

**Current backend status:** connected to the dedicated **PlacidWay Knowledge Assistant** project on Gabriel-Kelvin's Org **Free** plan (project `nakfsvmzgcroxbfuokpd`). The server writes topic statistics directly to Supabase and persists the seven-page public knowledge snapshot. Public reads/writes are blocked. Chat question/answer context remains temporary. No paid resources are required.

## Start locally

Requires Python 3.11 or newer. From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
# For a new checkout only; do not overwrite an existing configured .env:
Copy-Item .env.example .env
```

Populate `.env` with your Groq key, a strong admin password, a random session secret. The original development folder already has these configured locally. Never commit `.env` or copy its values into documentation. Generate fresh local secrets for another installation:

```powershell
.\.venv\Scripts\python.exe scripts/setup_secrets.py
```

The reviewed content snapshot is included. To read the seven source pages again:

```powershell
.\.venv\Scripts\python.exe -m app.ingestion
.\start.ps1
```

Open [the chat](http://127.0.0.1:8000) or [the admin workspace](http://127.0.0.1:8000/admin). The admin password is the local `ADMIN_PASSWORD` value. The server binds to loopback only. `APP_ORIGIN` must exactly match the browser origin; use `127.0.0.1`, not a different hostname.

## What is implemented

- Exactly seven allowlisted sources; robots checks, clear crawler name, paced requests, content hashes, conditional requests, change history, cached-content warnings, and manual refresh in admin.
- Separate adenocarcinoma, adrenal and anal package identities. English package prices come directly from table rows with USD, duration and inclusions. Wrong-price prompts do not supply evidence.
- Question routing for costs, package details, clinic information, video titles, comparisons, booking, quote requests, medical advice, off-topic questions and clarification.
- Temporary current-chat question/answer context (last eight turns), cleared by New conversation; relevant medical disclaimer once per chat; language-aware responses and RTL display. Original English citations remain available.
- Evidence drawer with exact source text, source URL and normalized line number. Internal validation metadata is not displayed.
- Protected admin metrics, popular topics, topic-grouped content gaps, source health and change history. Only Refresh and Sign out controls; no lead capture or exports. Supabase synchronizes permitted data automatically.
- Signed HttpOnly cookies, same-origin checks, request limits, per-IP abuse limits, admin login throttling, no client-side API keys, redacted operational errors, and retention cleanup.
- Health endpoint, bounded Groq calls/timeouts, friendly provider failures, mobile layout and streamed delivery of validated answers.
- Supplied PNG PlacidWay logo, coral/peach light theme, a single answer-evidence button, and browser Back/Forward history for chat and knowledge-source modules. Admin is a normal navigable page. At the first app history entry, Back can still return to the previous website; the app does not trap browser navigation.

## How answers are grounded

1. Apply deterministic safety and intent rules. Groq resolves questions requiring interpretation and translates non-English questions into retrieval terms.
2. Keep retrieval within the appropriate page identity. For package cost questions, use the matching package's table and inclusion sections directly. Similar package names never authorize cross-page substitution.
3. Retrieve normalized evidence lines with their surrounding context. Groq selects line IDs rather than writing unsupported factual prose. Returned IDs must belong to the provided evidence.
4. Assemble English answers from verified excerpts. Check exact quote/URL integrity, reject recognized instruction-like page text, enforce package identity, and verify every dollar token against cited evidence.
5. Translate when needed with Groq, checking preservation of numbers. English evidence remains unchanged. Translation is not guaranteed perfect; see limitations.
6. Only after validation, stream text to the browser. Status events appear while the server is working. This is validated delivery streaming, not raw unverified model-token streaming.

Refusals, clarification and missing-information messages are application behavior. Their source links are explicitly labeled as scope, context or contact guidance; the app does not fabricate a quote that “proves” something is absent.

## Tools and architecture

| Component | Choice and reason |
|---|---|
| Backend | FastAPI and Python: small, explainable modules for crawling, retrieval, validation, streaming and testing. |
| AI | Groq `openai/gpt-oss-20b`, verified against the supplied account's models endpoint. No other AI provider. No search or code-execution tools granted to the model. |
| Retrieval | Page identity + lexical passage ranking with context; appropriate for seven known documents and requires no paid embedding service. |
| Extraction | BeautifulSoup: explicit page-specific selectors, preserved tables, removed widgets and unrelated recommendations. |
| Frontend | Semantic HTML, CSS and vanilla JavaScript: no framework build step, no CDN dependencies, quick local startup. |
| Persistence | Supabase Postgres for topic metrics, errors, shared atomic rate limits and public source snapshots; process memory for temporary conversational context. No SQLite database. |
| Security | Python HMAC signed cookies; server-only database credentials. |
| Verification | Pytest security/infrastructure checks plus a 36-question live evaluation and saved answers to the eight required types. |

```text
Browser → FastAPI → safety/intent routing → seven-page evidence store
                    ↓ Groq interpretation / selection / translation
                 exact quote + price validation → validated SSE response
                    ↓
             Supabase topic metrics / errors / shared rate limits
```

## Supabase setup

Use a dedicated **Free** project. Do not upgrade or enable paid add-ons. Disable automatic table exposure and enable automatic RLS. Run `supabase/schema.sql` in the project's SQL editor or through an administrative database connection. All application tables have RLS enabled, no `anon` or `authenticated` grants, and explicit `service_role` grants. They are accessed only by the backend.

Set `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in `.env` locally, or as Render environment variables. Run both `supabase/schema.sql` and `supabase/cloud-runtime.sql`. Credentials are required: there is no local database fallback. Modern secret keys use the API-key header; legacy service-role JWTs additionally use Bearer authorization. Never put the server key in browser JavaScript.

Metrics and errors are written directly to Supabase. The dashboard aggregates in Postgres rather than downloading a limited page of records. Atomic database rate limits survive application restarts. On startup, the current public source snapshot is restored from Supabase. Refresh persists the new snapshot immediately; an in-process maintenance loop checks every minute while the service is awake. Failed metric writes use a bounded volatile retry buffer of 1,000 records; these pending records are lost if the process restarts during an outage. There is no local SQLite file. Topic records and errors are retained for 30 days and cleaned up while running. Current-chat turns stay in memory, are cleared on New conversation, and are lost on restart or a Free host cold start; no transcripts or contacts are persisted.

## Deploy to Render (Free)

Deploy this repository as a Python web service in Singapore on the Free plan. Build: `pip install -r requirements.lock.txt`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`. Set `PYTHON_VERSION=3.11.11`, `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `ADMIN_PASSWORD`, and a random `SESSION_SECRET` of at least 32 characters in Render's environment settings. `RENDER_EXTERNAL_URL` supplies the allowed HTTPS origin and secure cookie setting automatically; set `APP_ORIGIN` explicitly only for a custom domain. Health path: `/api/health`.

The included source JSON is a public-content bootstrap cache; Supabase holds the authoritative persistent snapshot. Do not add a disk, paid worker, or paid database. The Free service may sleep, delaying its next request and pausing maintenance. Use one application worker because chat context is intentionally temporary and process-local. The shared admin password is an assessment access mechanism; staff accounts and MFA would require further work.

## Test and submission files

Run the complete suite, including real Groq calls (31 infrastructure/security, conversation and cloud-sync tests and 36 question cases):

```powershell
.\.venv\Scripts\python.exe scripts/evaluate.py --live
```

This runs infrastructure/security tests and all 36 question cases, exits nonzero on failure, and writes:

- `reports/live-evaluation.md` and `.json`: actual pass/fail checks and answers.
- `reports/required-eight-answers.md`: actual answers and citations for the eight required test types.

For deterministic checks without spending API quota, run `python -m pytest -q`. The evaluation script without `--live` also exercises its offline test path, but that path is not a substitute for Groq behavior or multilingual validation. Evaluation records and counters are isolated from the running app and never synced to Supabase. Live runs are paced; free-tier quotas may still produce failures, which are reported rather than suppressed. `GROQ_DAILY_CALL_LIMIT` defaults to 100 to bound local usage. It counts provider calls, not chat messages, and is not a billing guarantee.

<!-- TEST_RESULTS_START -->
Live evaluation: **36/36 passed**, run 2026-10-09T10:54:55.098185+00:00. Infrastructure/security suite: **passed**. Current failed question cases: none.

The initial run was 32/36. Two questions exposed missing ‘how much’ routing, one Arabic cost question was over-refused, and one assertion incorrectly matched ‘approved pages’ as discount approval. These failures and their original answers are preserved in `reports/initial-evaluation.md` and `.json`. A repeated infrastructure run also exposed shared test rate-limit state; the tests now isolate their runtime state and never sync fixtures to Supabase.

See `reports/live-evaluation.md` for the current per-case report and `reports/required-eight-answers.md` for submission answers. Passing this finite suite does not guarantee perfect semantic accuracy or medical safety. These chatbot evaluation results are separate from the live cloud verification documented below. Seven-day uptime remains untested.
<!-- TEST_RESULTS_END -->

See `docs/source-review.md` for the page-by-page audit, `docs/assessment-extracted.txt` for the complete extracted brief, and `docs/limitations-and-next-week.md` for the submission write-up.

## Privacy and operations

Question/answer turns are held only in process memory, bounded to eight recent turns and a 24-hour idle expiry. New conversation deletes that context and rotates the chat cookie. A server restart clears all active conversation memory. No conversation transcripts are persisted or synchronized to Supabase. Topic summaries, random session identifiers and outcomes are retained for up to 30 days; the admin now reports popular/unanswered topics rather than storing individual questions. Basic email, phone and key redaction runs before temporary context storage and provider transmission; it is not guaranteed anonymization. Do not enter medical records. This app does not collect names, emails or quote requests. Quote and booking questions link to the official PlacidWay form. Admin exports and manual cloud-sync controls are removed; unanswered topics remain visible.

Cleanup runs while the service is awake. Deployment uses HTTPS, secure cookies, Supabase persistence and atomic shared rate limits. Staff identity/MFA, tested backups and uptime monitoring remain further work. Free hosting may sleep when idle.

Health: `GET /api/health`. Refresh: admin button or `python -m app.ingestion`. Error logs contain codes, not raw provider responses or credentials. A failed source fetch keeps the last successful snapshot. Refresh history stores added/removed lines and old/new price-bearing lines.

Answer length: package overviews and inclusions use up to eight content lines built from source excerpts. Lines wrap naturally on narrow screens; the app never clips answers with CSS. Source evidence retains the full original text.

Conversation update verification: `reports/conversation-regression.json` records the supplied two-turn example, a follow-up with additional inpatient details, one medical notice, and a reset followed by a fresh clarification. The first full run after the update passed 35/36; an unlisted-country cost question was misrouted as medical advice. That run is retained in `reports/context-update-first-evaluation.*`; an explicit cost-routing guard fixed it and the focused live retest passed.

Response formatting: eight content lines is a maximum, not a target. General package questions balance outpatient inclusions, inpatient inclusions, pricing/duration, follow-up and extra costs. Questions about a named tier focus on that tier. Simple currency and program-duration questions return one brief answer. General evidence selection is instructed to choose only the passages needed and distribute broad overviews across key aspects. Exact quotes remain accessible in the evidence drawer.

Latest formatting verification: **24/24 focused tests passed** and **14/14 targeted live cases passed**, recorded in `reports/live-evaluation-targeted.*`. The previous full 36-case evaluation retains its original timestamp.

Short-follow-up regression: the exact Anal-package → “Any idea about price?” sequence passed against the running HTTP server with cookies, as did reset isolation. Seven short cost phrasings were tested for each of the three package identities (21 combinations). New named treatments override current package context; ambiguous questions with active context are sent to the contextual router rather than immediately clarified. All 26 focused tests passed. Actual HTTP answers are saved in `reports/short-followup-regression.json`.

Deployment verification (2026-10-09): **31/31 infrastructure and security tests passed** after removing SQLite. Live Supabase startup/snapshot read and write, dashboard aggregation and concurrent atomic limits passed (3 accepted out of 8 attempts with a limit of 3). Live HTTPS tests passed for source/PNG loading, context, reset isolation, wrong prices, recovery unknowns, booking refusal, medical/off-topic refusals, Spanish responses, signed secure cookies, protected admin login/dashboard/sign-out and rejected foreign origins. See `reports/deployment-verification.json` for the actual deployed checks. Earlier Supabase/outbox reports describe the prior build and are historical; there is no pre-connection local backfill or durable local outbox in this deployment.

Admin simplification (2026-10-09): only Refresh seven sources and Sign out remain in the toolbar. Lead capture, contact storage, exports and the manual-sync API were removed. Automatic background syncing continues. The empty cloud/local lead tables were removed. Earlier reports describing the lead feature are historical and superseded by this change.


Latest hosted refresh: **warning, 0 changed pages**. The host could not read the crawling rules; all seven last-successful source contents were retained and the warning snapshot persisted to Supabase. The app remains usable from reviewed cached evidence, but this is not a successful live recrawl. See the deployment report for the actual status.
