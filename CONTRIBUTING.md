# Contributing

RiftSense is currently in beta. Small, focused changes are preferred over large
feature additions while release stability is being established.

## Before submitting a change

Run the offline regression and code-quality gates first:

```bash
python tools/run_tests.py
python tools/code_quality_audit.py
```

Then, on a machine with internet access, run:

```bash
python tools/run_release_checks.py
```

The release checks run the public-tree audit, regression suite, code-quality
audit, compile all Python sources outside the source tree, and validate build
recommendation candidates against current Riot Data Dragon metadata.

## Guidelines

- Do not commit Riot API keys, League Client credentials, PUUIDs, match-history
  exports, logs, caches, or personal settings.
- Keep Riot API writes narrowly scoped. Do not add pick/ban/queue/combat
  automation.
- Preserve the session-only API-key model.
- Prefer deterministic, testable recommendation logic.
- Keep the user-visible product label as `v1 Beta` until the release version is
  intentionally changed.
- Add a regression test for bug fixes where practical.
