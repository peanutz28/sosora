# Fresh-clone quickstart — 2026-10-18

Cloned the local repository with `git clone --no-hardlinks .
/private/tmp/sosora-quickstart-resume-20261018`, at integration commit
`bc5184f2d001de28e0611c1c7f37f514d508d5b8`. This checkout inherited no ignored
credentials, installed dependencies or uncommitted application changes. It tests
the committed integration snapshot, not the current concurrent application edits
or a GitHub clone after merge.

The original README failed immediately because `python` is unavailable. It also
placed a blocking backend and frontend in one shell block, left the shell inside
`backend` before `cd frontend`, and used a literal hero-message placeholder.
The revised instructions use Python 3.12, independent terminals and generate the
request from the actual seed response. The test command now uses the installed
virtual environment. The iOS server description now points to current setup docs.

Both dependency installs passed after network access was enabled. Port binding
also required sandbox network permission. Existing servers occupied 8000/3000,
so verification used the documented alternative ports 18000/13000 and the matching
`NEXT_PUBLIC_APP_API_URL`. No running filming server was stopped.

- Backend health passed; seed returned nine simulated incidents.
- Cached Beacon report affected exactly SOS-001 through SOS-005.
- Frontend dev server returned HTTP 200 and rendered HTML.
- Backend: 41 tests passed with three existing Pydantic warnings.
- Frontend: 16 tests passed.

Evidence: [smoke summary](evidence/release_readiness_2026-10-18/quickstart.json),
[backend tests](evidence/release_readiness_2026-10-18/backend_tests.txt),
[frontend tests](evidence/release_readiness_2026-10-18/frontend_tests.txt).
This check did not exercise live inference, a physical device or browser map
interaction. npm reported three dependency vulnerabilities (one moderate, one high,
one critical); dependency upgrades were not applied in this documentation task.

`backend/data/sosora.db-journal` was already absent and untracked; the ignore rule
now covers SQLite sidecars. Hosted frontend and backend health both returned HTTP
200: [saved check](evidence/release_readiness_2026-10-18/public_check.json).
