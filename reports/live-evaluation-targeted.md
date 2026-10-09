# Live evaluation

Run: 2026-10-09T11:07:19.586209+00:00

Passed: 14/14

Offline mode verifies deterministic behavior only; it does not validate Groq routing or translation. Live mode calls the configured Groq model. Assertions check observable behavior, source identity, price context, and quote integrity; they are not a clinical or exhaustive semantic audit.

| # | Scenario | Result | Failed checks |
|---|---|---|---|
| 1 | Required cost | PASS |  |
| 2 | Required comparison | PASS |  |
| 3 | Required procedure | PASS |  |
| 8 | Required wrong price | PASS |  |
| 9 | Package separation | PASS |  |
| 10 | Package separation | PASS |  |
| 15 | Clinic identity | PASS |  |
| 24 | Spanish | PASS |  |
| 25 | Arabic RTL | PASS |  |
| 27 | Follow-up care | PASS |  |
| 29 | Excluded services | PASS |  |
| 30 | Additional costs | PASS |  |
| 32 | Different package follow-up | PASS |  |
| 36 | Same package contextual price | PASS |  |