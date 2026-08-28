# Changelog

All notable RiftSense changes are documented here.

## [Unreleased] — v1 Beta

### Added
- Refactored storage, Riot HTTP/LCU networking, security policy, typed models, and role normalization into testable `riftsense/` modules.
- Added automated unittest and code-quality audit tooling plus basic Pyright configuration.
- Riot public requests now enforce an `*.api.riotgames.com` hostname whitelist and revalidate redirects.
- API Test worker now always reports exceptions instead of ending with an unexplained “worker finished without a result”.
- Managed rune page is now named `RiftSense - <Champion>` (for example `RiftSense - Nocturne`) and is renamed when the selected champion changes.
- Added role-specific Draft Champion Pools for Top, Jungle, Mid, ADC, and Support, with automatic migration from the legacy global pool.
- Added 800 ms Champion Select refresh while draft is active so new picks/bans re-rank suggestions quickly without rebuilding the whole application page.
- Added SAFE PICK / COUNTER PICK context from pick order and visible same-role enemies.
- Added deterministic Draft Fit Confidence (`HIGH` / `MEDIUM` / `LOW`), explicitly separate from win probability.
- Added `Why this pick?` details showing source, confidence, pick context, composition reasons, synergy, good matchups, and warnings.
- Added AUTOFILL / ROLE GAP and POOL BLOCKED warnings when the assigned role is not covered by the configured pool.
- Draft cards now distinguish `MY POOL` from `ROLE FALLBACK`; fallback fills empty slots but never ranks above a viable MY POOL champion.
- Redesigned General > Solo Rank Progress as a Ranked Ladder graph with a
  thin orange progression line, tier-tinted rank/division bands, Current/Peak/
  Change/Win Rate/Games metrics, promotion/demotion markers, peak marker,
  hover details, and compact win/loss result dots.
- General profile dashboard with ranked record, rank progression, Personal Coach,
  and 7D / 30D / 90D / 1Y / ALL rank-history ranges.
- Unified Game Assistant for draft, builds, and live intelligence.
- Role-based champion Tier List with S+ / S / A / B / C / D tiers.
- Redesigned Game History with compact match cards, selected-match analysis,
  objective icons, circular champion portraits, and Player Memory.
- Settings tabs for General, Riot & Sync, Meta, Champion Pool, and Diagnostics.
- Riot API Test API and Verify & Sync diagnostics.
- Automated current-Summoner's-Rift recommendation item audit.
- Runtime rotating logs, safe diagnostics export, and crash dialog.
- Command-line pre-push source and item audits.

### Changed
- Removed manual Ban Suggestions from Game Assistant; picked/banned champions are still excluded from champion recommendations.
- Removed Rune Automation controls, recommendations, status text, and manual import buttons from Game Assistant. Automatic rune import is now controlled only from Settings and retains the existing role/champion safety checks.

### Fixed
- Windows taskbar/titlebar identity now uses the native multi-size RiftSense `.ico` plus a stable `RiftSense.Desktop` AppUserModelID, preventing `python.exe` from supplying the visible app icon.
- `Why this pick?` now opens in a larger resizable scrollable dialog so long draft explanations are never clipped.
- Draft-only Game Assistant layout now expands the left Draft panel to the bottom of the workspace, eliminating the empty strip left behind when the Live/Build panel is hidden.
- Moved Game Assistant utility buttons from the bottom of the Build Assistant into a compact contextual top toolbar (`Refresh`, `Copy Summary`, `Item Images`, `About`).
- Enemy-jungler role mapping no longer guesses JUNGLE from Live Client player-list order; localized Smite is detected through Riot raw spell fields, and the identified enemy jungler receives a narrow dedicated `playerscores` refresh before rendering CS/KDA.
- Restored the missing regional Riot API route resolver used by ACCOUNT-V1 and MATCH-V5 (`EUROPE`, `AMERICAS`, `ASIA`, `SEA`).
- Off-role Draft loadouts no longer reuse jungle-only summoner/rune presets or suggest `Flash + Smite`; non-jungle auto-import is blocked unless an explicit role-specific rune preset exists.
- Meta Consensus is explicitly Jungle-only in the beta so Top/Mid/ADC/Support cannot consume cached jungle build/rune data.
- Meta refresh workers now return results through a queue and never call Tkinter from a background thread.
- Legacy persisted Riot API-key fields are removed from settings, and fresh installs default automatic rune import to off.
- Rune import now revalidates champion + assigned role inside the background LCU worker immediately before any write, so stale jungle choices cannot leak into an off-role import.
- Legacy Riot API-key fields are stripped from restored data and newly created backup ZIPs as defense in depth.
- Removed the non-item `defensive boots` placeholder from the Nasus baseline so the current-SR recommendation audit can validate every static candidate.
- Data Dragon duplicate item names now resolve deterministically to the normal purchasable Summoner's Rift variant instead of depending on JSON order (for example normal BORK vs mode-specific BORK).
- Standalone pre-push item audit now adds the source root to `sys.path` before importing the extracted `riftsense` package.
- Draft Assistant no longer suggests champions that are banned or already picked by either team.
- Riot Champion Select roles are normalized correctly (`MIDDLE` → Mid, `BOTTOM` → ADC, `UTILITY` → Support).
- If MY POOL does not cover the assigned role, Draft Assistant now fills the missing Top 3 slots from a conservative role-specific fallback pool instead of showing nothing.
- Cleaned up the Ranked Ladder progression curve: removed spline overshoot, reduced line/glow thickness, removed the opaque under-line fill so tier colors remain visible, tinted all Gold divisions warm/yellow and Platinum divisions cool/blue, and replaced W/L result letters with compact green/red dots.
- `MonkeyKing` is displayed as `Wukong`.
- Ranked LP refresh and ranked-history synchronization reliability.
- ACCOUNT-V1 403 fallback through saved/local League Client PUUID.
- Arena/Prismatic items such as Lightning Rod leaking into SR builds.
- Intermittent missing boots while current-patch item data was still loading.
- History layout rebuild/shake and splitter behavior.
- Rank-range buttons now use real time on the chart x-axis.

### Security
- Riot Developer API key remains in memory only.
- Public-source audit blocks API-key-shaped tokens and local runtime data.
- Runtime log output redacts API-key-shaped secrets.

## Repository status

The application is pre-1.0 beta software. Interfaces and local data schemas may
still change before the first stable release.
- Rebuilt the Windows taskbar/titlebar icon from the compact RiftSense RS logo.
- Rebuilt the Windows icon directly from the user-selected compact RiftSense logo artwork.
- Force-applied the app icon to the native Windows HWND so source launches do not retain the Python taskbar icon.
- Changed the Windows AppUserModelID once for v1 Beta so Explorer does not reuse the previously cached taskbar icon.
