# RiftSense

**Live Intelligence for League of Legends**

RiftSense is a local-first Windows desktop assistant for League of Legends. It
combines draft context, adaptive builds, live-game information, ranked-history
review, tier lists, and persistent player coaching in one interface.

> Status: **v1 Beta / pre-1.0**

## Current features

- **General** — Solo/Duo rank, wins/losses, win rate, recent form, a ranked-ladder
  progress chart with rank bands, orange LP curve, milestones, match-result strip,
  hover details, most-played champion, and Personal Coach.
- **Game Assistant** — role-specific champion pools; sub-second Champion Select re-ranking; picked/banned-champion exclusion; safe/counter-pick context; draft-fit confidence; `Why this pick?` explanations; role-gap/autofill warnings; adaptive full builds, situational items, jungle companion guidance, live team/enemy context, objectives, gank priority, and lane/power comparison.
- **Tier List** — role-specific S+ / S / A / B / C / D champion tiers.
- **Game History** — ranked match feed, scoreboard, analysis, builds, vision,
  objectives, same-role comparison, trends, champion performance, and Player
  Memory.
- **Riot & Sync** — session-only Riot API key, `Test API`, and `Verify & Sync`.
- **Meta Consensus** — optional cached public build-source consensus for Jungle
  with current-patch SR item validation. Non-jungle roles use only explicit
  role-specific local presets in the beta.
- **Diagnostics** — local service state, Data Dragon health, ranked-sync state,
  item audit, safe copyable diagnostics, and rotating runtime logs.

## Requirements

- Windows 10/11
- Python 3.11+ for source execution
- League of Legends / League Client for local draft and live integration
- A temporary Riot Developer API key for Riot Web API ranked-history sync

The current source build uses Python's standard library only at runtime.

## Run from source

```bash
python RiftSense.py
```

## Riot data and local APIs

RiftSense uses:

- Riot Data Dragon for patch-aware champion, item, and rune static data.
- Riot Web APIs for ranked account/rank/match synchronization.
- The local League Client API for local client context and narrowly scoped rune
  page management.
- The local Live Client Data API for live-match information.

League Client endpoints are local/unsupported interfaces and may change after a
League Client update.

## Privacy and data storage

User data is stored outside the application source directory. Existing beta
installs currently retain the legacy version-independent folder name:

```text
%LOCALAPPDATA%\RiftBuildAssistant
```

This preserves previous settings, history, cache, Player Memory, and backups
during the RiftSense rename.

The Riot Developer API key is **session-only** and is not intentionally written
to settings, backups, diagnostics, or logs.

## Competitive integrity

RiftSense does not:

- read League process memory;
- inject DLLs;
- automate combat or movement;
- automate picks, bans, or queue actions;
- automatically track enemy Flash/ultimate cooldowns.

Rune automation is limited to a single managed RiftSense rune page through
local League Client rune endpoints. Its only user-facing control is the
**Settings → General** auto-import toggle; Game Assistant does not expose rune
automation controls. Automatic rune import is opt-in on fresh installs and is
blocked for non-jungle roles unless an explicit role-specific preset exists.

## Pre-release checks

In the app:

1. `Settings → Riot & Sync → Verify & Sync`
2. `Settings → Meta → Audit Recommended Items`
3. `Settings → Diagnostics → Run Pre-Release Check`

From the source tree:

```bash
python tools/run_release_checks.py
```

The public-source audit rejects secret-shaped tokens, local runtime data,
compiled Python files, local logs/caches, and other release-tree contamination.

## Logs and crash diagnostics

Runtime logs are written to the local data folder under `logs/riftsense.log`.
They rotate automatically and redact Riot API-key-shaped values. The
Diagnostics tab can copy a safe status report without exposing the API key,
Riot ID, PUUID, or Windows username.

## Project status / release plan

The immediate release sequence is:

1. pass real-machine `Verify & Sync`;
2. pass item and source audits;
3. push the cleaned source tree;
4. build the Windows executable/installer;
5. create a GitHub beta release;
6. add release/update notification support.

## Disclaimer

RiftSense is an unofficial third-party project. It is not endorsed by Riot Games
and does not represent Riot Games or League of Legends. Riot Games, League of
Legends, and related trademarks and assets are property of their respective
owners.


### Engineering / safety

The beta now includes a layered `riftsense/` package for storage, security, Riot networking and typed models, plus an automated regression suite. Rune imports manage one page whose name follows the selected champion, e.g. `RiftSense - Nocturne`.
