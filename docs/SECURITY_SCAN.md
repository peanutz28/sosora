# Full-history secret scan — 2026-10-18

Gitleaks 8.30.0 scanned all locally available refs in this non-shallow repository:
76 reachable commits; the scanner processed 73 commits with changes, approximately
58.38 MB. Snapshot HEAD: `bc5184f2d001de28e0611c1c7f37f514d508d5b8`.
Remote refs were not refreshed; unreachable/dangling objects, ignored local secrets
and subsequent commits are outside this scan.

Command (no secret values printed):

```bash
gitleaks git . --log-opts='--all --full-history' --redact=100 \
  --no-banner --no-color --ignore-gitleaks-allow \
  --report-format=json --report-path=/private/tmp/sosora-security/history-redacted.json
```

The scanner exited 1 with six candidates. Manual source inspection classified all
six as false positives: three SHA-256 source integrity digests, one public
base-image GPG fingerprint, and two occurrences of a browser localStorage queue
key. No authentication credential was identified. This is a scanner result, not
proof that no secret exists. No suppressions or history rewrites were added.

[Sanitized findings](evidence/release_readiness_2026-10-18/secret_findings.json)
contain only rule IDs, file locations, commits, scanner fingerprints and reasons;
matched values and source snippets are omitted. The raw redacted report stays in
temp storage. If any candidate is later confirmed sensitive, revoke/rotate it
before coordinating history cleanup.
