# RiftSense v1 Beta — Pre-Release Checklist

## Automated local gates

- [x] Python source compiles.
- [x] Automated `unittest` regression suite passes.
- [x] Code-quality audit reports no duplicate top-level functions and no more than three intentional broad silent logging handlers.
- [x] Riot public API host allowlist and localhost-only LCU security tests pass.
- [x] Dynamic rune-page naming regression (`RiftSense - Champion`) passes.
- [x] Off-role rune-worker safety regression blocks stale Jungle presets before LCU writes.
- [x] Backup regression strips legacy Riot API-key fields from settings/account JSON.
- [x] Static recommendation candidate list contains only concrete item names (no generic boot placeholders).
- [x] API Test worker exception-reporting regression passes.
- [x] Dark and Light UI smoke-tested.
- [x] Headless navigation smoke-tested at 1200×700, 1600×900, and 1920×1080.
- [x] Game Assistant UI smoke-test confirms Ban Suggestions and rune-automation controls are absent; Settings retains the automatic-rune-import toggle.
- [ ] 100%, 125%, and 150% Windows DPI smoke-test on the real target machine.
- [ ] Manually smoke-test General, Game Assistant, Tier List, Game History, Settings, and Diagnostics before release.
- [x] Public source audit passes.
- [x] Secret/log/runtime-data exclusions are covered by `.gitignore` and the public audit tool.
- [x] Recommendation item audit regression blocks Arena/Prismatic candidates such as Lightning Rod.
- [x] Rotating runtime logging and secret redaction are enabled.
- [x] Safe copyable Diagnostics are available.
- [x] Crash callback logging/dialog is enabled.

## Real-machine gate before first push/release

- [ ] Open League Client and log in.
- [ ] Generate a fresh temporary Riot Developer API key.
- [ ] Open `Settings → Riot & Sync`.
- [ ] Run **Verify & Sync**.
- [ ] Confirm PUUID resolution succeeds.
- [ ] Confirm League-V4 returns HTTP 200.
- [ ] Confirm Match-V5 list returns HTTP 200.
- [ ] Confirm at least one Match-V5 detail can be read when a ranked match exists.
- [ ] Confirm full ranked History sync completes.
- [ ] Run `Settings → Meta → Audit Recommended Items` against the loaded live patch.
- [ ] Run `Settings → Diagnostics → Run Pre-Release Check`.
- [ ] Check the main window at Windows display scaling 100%, 125%, and 150%.

## Source push gate

From the cleaned source folder:

```bash
python tools/run_release_checks.py
```

Then review `git status` before pushing. No local history, logs, cache, keys,
settings, previews, archives, executables, or compiled Python files should be
staged.

## Licensing

The current `LICENSE` uses a conservative **All Rights Reserved** source-viewable
notice. Replace it with MIT, Apache-2.0, GPL, or another license before release
if you intentionally want to grant broader reuse rights.
