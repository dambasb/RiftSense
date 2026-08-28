RIFTSENSE v1 BETA — ADVANCED DRAFT ASSISTANT

WHAT IS NEW
- Fixed General > Solo Rank Progress range buttons appearing to do nothing when all saved LP snapshots were from the same recent week.
- The graph now uses real snapshot timestamps on the x-axis instead of spacing every point evenly from left to right.
- 7D / 30D / 90D / 1Y now represent actual calendar windows.
- If RiftSense only has seven days of LP history, selecting 30D/90D/1Y shows that history in the correct recent portion of the wider window instead of stretching it across the whole chart.
- ALL uses the entire retained tracking period from the oldest stored LP snapshot to the newest.
- The x-axis now shows the selected range boundaries rather than always showing only the first/last stored snapshot.
- The chart note explicitly shows when LP tracking began and explains empty space before that date.
- The selected range continues to persist between sessions.
- Existing long-term snapshot retention, Verify & Sync, item audit and immediate-boots fixes are retained.
- Public product version remains v1 Beta.

- Added a time-range selector to General > Solo Rank Progress.
- Available views: 7D, 30D, 90D, 1Y and ALL.
- The selected range is saved and restored between RiftSense sessions.
- Default progress range is 90D.
- Removed the old display cap that limited the rank chart to the latest 80 snapshots.
- ALL can now draw the full retained rank-progress archive.
- Rank-progress storage was increased from 300 to 2,000 changed-rank snapshots.
- 1Y and ALL use year-aware x-axis date labels.
- If the selected range contains fewer than two rank snapshots, RiftSense explicitly suggests selecting a longer range instead of silently switching chart meaning.
- The rolling win-rate fallback also respects the selected time range.
- Existing Verify & Sync, recommendation-item audit and immediate-boots fixes are retained.
- Public product version remains v1 Beta.

- Fixed an intermittent live-build issue where boots could be missing for the first part of a match and appear only later.
- Root cause: RiftSense could consider the live patch "loaded" because the Data Dragon version string matched even when the current patch item catalogue had failed to load.
- Patch refresh now requires current item/champion static data to be ready before treating a matching version as healthy.
- Missing item data retries quickly instead of waiting on the old long patch-refresh interval.
- When current item data arrives, build/adaptive signatures are invalidated immediately so icons and ids rerender on the next live refresh.
- Adaptive Full Build now always reserves slot 1 for boots.
- If Data Dragon item metadata is temporarily unavailable, RiftSense still shows the selected boot name immediately instead of omitting the slot.
- The temporary boot slot shows BOOT / loading-data state until the real current-patch item id/icon becomes available.
- Once item data arrives, the same slot is revalidated and upgraded to the normal boot icon/source.
- Existing pre-push Verify & Sync and recommendation-item audit are retained.
- Public product version remains v1 Beta.

- Added Settings > Riot & Sync > Verify & Sync for the real-installation pre-push check.
- Verify & Sync validates the live pipeline in this order: PUUID resolution -> League-V4 -> Match-V5 list -> Match-V5 detail.
- Only after all verification stages pass does RiftSense launch the normal full ranked-history sync.
- Verify & Sync uses the existing session-only API key and never persists it.
- Added an automated recommendation-item audit that scans every upstream static/cached item source used by RiftSense.
- The item audit covers profiles.json build paths + boots, adaptive pools, assassin pools/cores, threat-weight items and cached Meta Consensus candidates.
- Settings > Meta now shows ITEM AUDIT status and includes an Audit Recommended Items button.
- A silent item audit runs after Data Dragon loads on startup.
- Invalid/stale/mode-only candidates remain blocked by the central current-Summoner's-Rift validator and are now also reported with the exact source and rejection reason.
- Added tools/pre_push_audit.py for a command-line pre-push check against the latest Riot Data Dragon item data. It exits non-zero if any recommendation candidate is invalid.
- Regression coverage includes Lightning Rod injection, candidate-source collection, Verify & Sync handoff, Dark 100% UI and Light 150% UI.
- Public product version remains v1 Beta.

- Fixed the remaining ranked-sync failure shown as "Could not resolve Riot ID / API key rejected".
- The sync no longer requires ACCOUNT-V1 before every history sync.
- RiftSense now resolves the user's PUUID in this order:
  1. previously saved PUUID for the same Riot ID
  2. read-only local League Client current-summoner identity
  3. Riot ACCOUNT-V1 only as a fallback
- This lets personal desktop sync continue when ACCOUNT-V1 returns HTTP 403 but League-V4 and Match-V5 are usable.
- A League Client account mismatch is detected and reported instead of silently syncing a different account.
- HTTP 403 from ACCOUNT-V1 is no longer automatically labelled as a bad/expired key because Riot documents 403 as ambiguous between authorization and unsupported/incorrect path.
- Added Settings > Riot & Sync > Test API.
- Test API performs a no-write diagnostic:
  PUUID resolution -> League-V4 -> Match-V5
  and shows the exact stage and HTTP status.
- Full sync now reports League-V4 authorization separately from identity resolution.
- Existing immediate Apply & Save sync, visible progress/status, History cache refresh, item-mode filtering and History UI fixes are retained.
- Public product version remains v1 Beta.

- Reworked the ranked sync lifecycle because the previous Apply & Save -> Game History flow could look idle even while a background request was starting.
- Apply & Save now starts one ranked-history sync immediately when a session API key is present; opening Game History is no longer required to trigger it.
- Settings > Riot & Sync now shows the live sync status text and progress bar directly below the API key section.
- Game History now has a persistent sync feedback strip with the exact current phase/error plus a progress bar and Cancel action.
- The Game History header shows SYNCING from the first account/rank/match-list request, even while progress is still 0%.
- Sync Ranked is disabled and changes to Syncing... while a worker is active; Cancel is enabled only while a worker is active.
- Stale events from a previous sync are cleared before a new worker starts.
- start_riot_history_sync now returns real success/failure so the auto-sync flow cannot report that a sync started when it did not.
- Terminal sync events invalidate the History row cache and perform a full History refresh, ensuring newly downloaded matches appear immediately.
- API-key/HTTP failures remain visible in both Settings and Game History instead of collapsing back to a misleading READY state.
- The API key remains session-only and is never persisted.
- Existing Summoner's Rift item-mode filtering, History redesign and prior fixes are retained.
- Public product version remains v1 Beta.

- Fixed Arena/prismatic items leaking into Summoner's Rift build recommendations.
- Lightning Rod is now explicitly blocked from SR recommendations.
- Added a generalized extended-item-ID filter so Arena/prismatic special-distribution items cannot pass simply because Data Dragon contains the item.
- Recommendation validation now also rejects static descriptions that identify Prismatic Item / Prismatic Anvil / Arena-only distribution.
- Third-party meta scraping now builds its candidate catalogue from the same strict current-Summoner's-Rift validator used by live recommendations.
- Existing meta caches may still contain old names, but invalid mode-only items are vetoed before scoring/rendering.
- The fix applies to Adaptive Full Build, Situational Item Options, meta candidates and future scraped item candidates.
- Public product version remains v1 Beta.

- Fixed the Settings > Riot & Sync flow when a new session API key is entered.
- Apply & Save now arms one ranked-history sync for the next time Game History is opened.
- Opening Game History after Apply & Save automatically starts Sync Ranked with the newly entered in-memory API key.
- The automatic sync runs only once per Apply & Save action; normal navigation back to History does not trigger repeated API calls.
- The API key remains session-only and is never written to settings.json, riot_account.json, backups or logs.
- Riot ID, platform and route stay synchronized between Settings and Game History; route is now also written to the non-secret account snapshot.
- Settings now explicitly explains that Apply & Save followed by opening Game History starts one automatic ranked sync.
- If another ranked-history sync is still running, the armed sync waits briefly instead of silently dropping the newly applied key.
- Public product version remains v1 Beta.

- Fixed General > Refresh Rank so it can refresh the current ranked snapshot without requiring a full Match-V5 history sync.
- Refresh Rank now prefers Riot League-V4 when a session API key is already entered in Settings > Riot & Sync.
- If the Riot API key is missing/unavailable, Refresh Rank falls back to the local League Client ranked endpoint.
- The Refresh Rank button now shows Refreshing... and is disabled while the request is running.
- General Wins / Losses / Win Rate now use the fresh Solo/Duo rank snapshot when available instead of remaining tied to the older tracked-history count.
- A successful rank refresh updates LP, Wins, Losses, Win Rate, rank source/timestamp, rank progress and the History rank card.
- A failed refresh clearly says that the previous snapshot is still being displayed instead of silently appearing to do nothing.
- Added strict current-Summoner's-Rift item validation for build recommendations.
- An item name existing in Data Dragon is no longer enough to make it recommendable.
- Recommendations now reject non-purchasable, map-disabled, hidden/non-store, champion-specific and consumable/trinket entries.
- Full-build slots also reject normal components that still build into another non-boot item.
- Adaptive options, assassin cores, meta candidates, baseline/fallback items and boots all pass through current-patch validation.
- Invalid/removed baseline items are hidden instead of being rendered as a ? recommendation.
- Public product version remains v1 Beta.

- Fixed Riot/Data Dragon internal champion id MonkeyKing displaying in History; it is now shown as Wukong while the raw id is preserved for icon lookup.
- The Wukong display-name fix applies to match cards, Selected Match, Most Played, champion performance, scoreboard and enemy-role comparison.
- Rebuilt the top ranked summary with a responsive Grid layout so Rank, Wins, Losses, Win Rate, Last 10, Streak and Most Played are distributed evenly across the full width.
- Removed the large empty gap that could appear between Streak and Most Played on wide windows.
- Last 10 now uses thin 13x6 pixel result bars like the target design rather than square text-unit labels.
- Match Summary body text was increased for easier reading and given a wider wrap area.
- Existing rank crest, circular champion portraits, custom History tabs, objective icons, navigation caching and splitter debounce are retained.
- Dark, Light, 100% and 150% DPI layouts were re-tested.
- Public product version remains v1 Beta.

- Reworked the remaining Game History visual differences from the target screenshot.
- Added a real crest-style ranked image area instead of the previous text/geometric GII badge.
- Gold uses the supplied target-reference crest artwork; the other tiers use matching RiftSense crest assets so the UI can still adapt when rank changes.
- History champion portraits are now circular with an accent ring in the match feed, Most Played, Selected Match and player-vs-enemy comparison.
- Added dedicated History tab icons for Matches, Champions, Trends and Player Memory.
- Replaced the platform-looking ttk tab headers with custom flat tab bars and a gold selected underline.
- The Selected Match tabs also use a custom flat target-style tab bar.
- Added objective icons for Dragon, Baron, Rift Herald and Towers.
- Objective cards now show icon + objective name + count instead of text-only boxes.
- Circular champion masking is implemented with Tk PhotoImage, so RiftSense remains stdlib-only at runtime.
- Existing History navigation caching and splitter-resize debounce remain enabled.
- Dark, Light, 100% and 150% DPI layouts were re-tested.
- Public product version remains v1 Beta.

- Rebuilt Game History against the supplied target screenshot rather than the earlier approximate mockup.
- History now hides the generic RiftSense topbar and uses the full workspace height, matching the target composition.
- Top ranked summary now uses a compact geometric rank crest, Wins, Losses, Win Rate, Last 10 result blocks, Streak and Most Played.
- Match/Champions/Trends/Player Memory tabs use a dedicated flatter History tab style with accent-selected labels.
- Match filters now use the target single-row layout: search placeholder, Solo/Duo chip, Flex chip, result dropdown and compact scope menu.
- Match cards were rebuilt with fixed compact columns for WIN/LOSS, champion portrait/name, colored K/D/A + KDA ratio, CS + CS/min, duration/date and action.
- Selected Match header now follows the target: result, champion portrait, Champion • Role • Queue, date/time/duration/patch and a compact action button.
- Selected Match has Overview, Scoreboard, Analysis, Build and Vision tabs.
- Overview now shows KDA, CS, KP, Gold and Vision as large primary values with secondary rate/context lines.
- Objectives display the player's team objective totals as Dragon / Baron / Rift Herald / Towers cards.
- Performance vs Enemy Role now uses player portrait + three stats + VS + enemy stats + enemy portrait.
- Match Summary shows multiple evidence-based strengths/review points and a larger role-edge/final-gold visual.
- History navigation no longer rebuilds the 30-card feed or resets its divider when leaving and returning.
- Active History clicks are no-ops; search/result filtering uses cached rows; splitter relayout remains debounced.
- Sidebar footer now exposes readiness, patch and platform like the target layout.
- Dark, Light, 100% and 150% DPI layouts were re-tested.
- Public product version remains v1 Beta.

- Game History was visually rebuilt against the supplied/reference mockup, not just functionally rearranged.
- Top ranked summary now follows the reference hierarchy: Solo rank, Wins, Losses, Win Rate, Last 10 with ten colored result blocks, Streak and Most Played with champion portrait.
- Matches use dense master/detail cards with a colored result strip, champion portrait, WIN/LOSS, champion, queue/role, date, KDA, CS, CS/min and duration.
- Selected Match now uses five compact primary metrics: KDA, CS, KP, Gold and Vision.
- Objectives are displayed as four separate Dragon / Baron / Rift Herald / Towers cards.
- Same-role comparison is now a dedicated Performance vs Enemy Role panel with Gold, CS/min, Vision/min and Objective Damage deltas.
- Match Summary shows one strongest positive stat signal, one primary review point and a role-edge gauge.
- History navigation no longer rebuilds all 30 cards every time the user leaves and returns.
- The History master/detail sash is positioned only on the first open and is preserved afterward.
- Clicking the already-active Game History navigation item is now a no-op instead of another layout cycle.
- Search/result filtering uses the cached history rows and does not recalculate Champions, Trends, Player Memory and General on every keystroke.
- The existing splitter-resize debounce remains active.
- Public product version remains v1 Beta.

- Reworked Game History again to match the previously proposed visual mockup instead of only changing the underlying layout.
- Match rows now always show the champion portrait, WIN/LOSS state, champion name, queue/role, date, KDA, CS, CS/min and duration.
- The match-card layout now uses fixed Grid columns so the champion/result section cannot disappear when the master/detail divider is narrow.
- History uses a strong master/detail hierarchy: compact match list on the left and a larger selected-match workspace on the right.
- Top summary now focuses on Solo rank, Record, Win Rate, Last 10 and Streak; Most Played remains in the Champions area instead of competing for space.
- Selected Match Overview uses four primary metric cards (KDA, CS/min, KP, Gold) with Vision/min as a compact secondary metric.
- Filters are compressed into two small rows directly above the match list.
- Initial History rendering remains limited to 30 cards with Load More for performance.
- Divider-resize debouncing from the previous performance build is retained.
- Public product version remains v1 Beta.

- Fixed the Game History master/detail divider feeling laggy while its width is dragged manually.
- The match-card Canvas no longer resizes hundreds of child widgets on every single sash pixel.
- Match-card width updates are now debounced and applied once after the divider movement pauses.
- Scrollregion recalculation is also debounced to avoid feedback geometry passes during resizing.
- Initial History rendering now creates 30 match cards instead of 60; Load More continues to expose additional matches on demand.
- The Canvas viewport still moves immediately during the drag, so the splitter follows the mouse while the expensive card relayout waits until the drag settles.
- Public product version remains v1 Beta.

- Rebuilt Game History around a clearer master/detail layout based on the approved mockup.
- The top area is now one compact ranked summary hero instead of a stack of dashboard boxes.
- Solo rank/LP is visually dominant; Flex rank is secondary. Record, Win Rate, Last 10, Streak and Most Played sit in one horizontal summary bar.
- Sync Ranked and Sync Settings now live in the Game History header; the separate sync toolbar/card was removed.
- History tabs are simplified to Matches, Champions, Trends and Player Memory.
- Matches now use visual cards instead of an Excel-like Treeview table.
- Every match card groups result, champion, queue/role, KDA, CS, CS/min, duration and date into two scan-friendly lines.
- Selected matches use an accent border; wins/losses use a thin green/red status strip.
- Search, Solo/Duo, Flex, result filter and scope now live directly above the match list.
- The selected-match pane receives more horizontal space than the match list.
- Overview now has five primary metrics: KDA, CS/min, Kill Participation, Gold and Vision/min.
- Long histories are progressively rendered 60 matches at a time with Load More, keeping the new card UI responsive even with 200+ stored games.
- Riot ID / platform / route / API key remain in Settings > Riot & Sync; API key remains session-only.
- Exact rank LP still refreshes from the local League Client when available.
- Dark, Light, 100% and 150% DPI layouts were regression-tested.
- Public product version remains v1 Beta.


DRAFT CHAMPION POOL
The default draft pool is stored in:

  draft_profiles.json

The included pool is:
- Wukong
- Nocturne
- Jarvan IV
- Amumu
- Maokai
- Warwick
- Vi
- Jax
- Shen
- Nasus

You can remove champions or edit their values in draft_profiles.json.

IMPORTANT ABOUT DRAFT SCORES
Draft scores are local composition heuristics. They consider factors such as:
- AP/AD balance
- frontline
- engage
- crowd control
- Yasuo knock-up synergy
- visible enemy tankiness / squishiness

They are NOT live patch win-rate statistics and the app does not contact third-party
statistics websites.

LEAGUE CLIENT CONNECTION
While Champion Select is open, V6 reads the local League Client API in read-only mode.
It obtains the temporary local port/password from League's own lockfile.

The League Client API is an unsupported local Riot service. Riot may change local
endpoints after a client update. If a future League update breaks draft detection,
the app may need an update.

If your League installation is not in a common folder:
1. Start the app.
2. Click "Select League Folder".
3. Choose the folder that contains LeagueClient.exe / the League "lockfile".

RUNNING THE APP
1. Extract the ZIP.
2. Open a terminal in the extracted folder.
3. Run:

   py -3 RiftBuildAssistant.py

If "py" is unavailable:

   python RiftBuildAssistant.py

REQUIREMENTS
- Python 3
- Tkinter (normally included with the standard Windows Python installer)
- No extra Python packages required

NETWORK / SECURITY
Local read-only connections:
- League Client (LCU): https://127.0.0.1:<League local port>/
- Live game: https://127.0.0.1:2999/

Internet:
- Riot Data Dragon only, for champion/item metadata and icons:
  https://ddragon.leagueoflegends.com/

The app:
- does not read process memory
- does not inject DLLs
- does not auto-pick or auto-ban
- does not click League UI
- does not require your Riot username/password
- does not require a Riot API key


TIER BADGES
Tier values are stored in:

  tier_data.json

The included values are a snapshot for Jungle and are intentionally separate from
the dynamic 1-10 composition-fit score. You can edit tier_data.json at any time
without changing the recommendation algorithm.

Current included tier snapshot:
- Source: Mobalytics
- Patch: 26.15
- Scope: Jungle, Emerald+

A tier badge describes general tier-list strength from that snapshot.
The 1-10 score describes how well that champion fits the CURRENT visible draft.
Those two values can therefore disagree, which is expected.

Example:
A B-tier champion can still be the #1 recommendation if it fits your exact team
composition better than an S-tier champion.


PANEL VISIBILITY
At the top of the app there are two toggles:

  Show Draft Assistant
  Show Live Build Assistant

Both data modules continue refreshing in the background even if their panel is hidden.
This means you can hide Draft after the draft ends, then immediately show it again
later without restarting the application.

SCROLLING
The Draft and Live sections are inside one vertically scrollable area. You can use:
- the scrollbar on the right
- the mouse wheel

This prevents the recommended build from being pushed below the visible window when
Draft recommendations take up more vertical space.


V9 THREAT-AWARE LIVE ITEMS

V9 reads the item lists already exposed by Riot's local Live Client Data API for
players in the current game. It then inspects Riot Data Dragon item stats and
descriptions to estimate visible pressure such as:

- physical damage
- magic damage
- critical-strike pressure
- attack-speed/basic-attack pressure
- lifesteal / sustain
- armor stacking
- crowd control / burst context

The application shows up to THREE situational item OPTIONS. It intentionally does
not auto-buy anything and does not present one mandatory "buy this now" instruction.

Examples:
- More visible physical/crit pressure can raise Death's Dance or Randuin's Omen.
- More visible AP pressure can raise Maw of Malmortius or Kaenic Rookern.
- Visible armor stacking can raise Black Cleaver.
- Visible sustain can raise Thornmail for tank profiles.

The normal champion-composition baseline build still appears below the situational
options.

VISIBLE DATA ONLY
V9 uses:
- normal Live Client player/champion data
- scoreboard-visible item inventories
- Riot Data Dragon static item metadata

It does NOT use:
- process memory
- DLL injection
- fog-of-war/hidden state
- automatic clicks or purchases


V10 FEATURE 1 — AUTOMATIC MODE SWITCHING

When "Auto Switch" is enabled:
- Champion Select detected -> Draft Assistant is shown and Live Build is hidden.
- Live game detected -> Draft Assistant is hidden and Live Build expands.
- Neither detected -> both waiting panels are restored.

The manual Draft/Live visibility toggles remain available. Automatic visibility is
only re-applied when the detected state changes, so you can still manually override
the view during the same state.

V10 FEATURE 2 — NEXT PURCHASE ASSISTANT

The app reads:
- current gold from the Live Client API
- your current inventory
- Riot Data Dragon item recipe trees and item gold values

It chooses the next target in this order:
1. unfinished CORE item
2. highest-fit situational option
3. current baseline situational item

It then shows up to three useful purchases for the current recall. If the target can
be completed immediately, it shows the completion cost. If nothing useful is
affordable, it shows the cheapest useful component and how much more gold is needed.

V10 FEATURE 3 — CORE VS SITUATIONAL

CORE is calculated as the longest common item prefix shared by the balanced, magic
and physical profile paths.

The rest of the currently selected composition path is displayed separately as:

  SITUATIONAL BASELINE

The live threat-aware situational options remain a separate section above it.

V10 FEATURE 4 — ENEMY THREAT PANEL

The panel shows up to five enemy champion cards. Each card summarizes the strongest
currently visible signals, for example:

  Physical HIGH
  Crit MED
  Magic HIGH
  Sustain MED
  Armor HIGH

Hover the champion portrait to see the enemy's currently visible items.

All threat analysis remains based on data exposed by the normal local Live Client
API and Riot Data Dragon static metadata.


V11 — JUNGLE COMPANION ADVISOR

When Smite is detected, the Live Build Assistant now shows all three jungle
companion starters:

- BLUE  — Gustwalker Hatchling — mobility
- GREEN — Mosstomper Seedling — durability / shielding
- RED   — Scorchclaw Pup — offensive pressure / slow

The application scores all three based on:
- champion preference
- enemy CC
- mixed damage pressure
- how squishy or tanky the visible enemy composition is

All three remain visible so the user can choose. The highest-fit option is marked
SUGGESTED.

If no jungle companion is currently owned, Next Purchase Assistant prioritizes the
highest-fit companion before normal core items.

The item ID and icon are resolved from the currently loaded Riot Data Dragon item
metadata by item name, so the app does not hardcode old item IDs.


V12 — WHY THE JUNGLE ITEM DISAPPEARS

The jungle companion starter is intentionally consumed/removed from the inventory
when the pet reaches its final evolution. Therefore, "starter not in inventory" is
not enough to decide that the user needs to buy a jungle item.

V12 now checks the Smite evolution state:
- base Smite -> quest not completed
- Unleashed Smite / intermediate upgraded state -> quest still in progress
- Primal / fully upgraded 1400-damage Smite -> quest completed

Once the quest is complete:
- Jungle Companion panel shows QUEST COMPLETE
- Next Purchase Assistant stops offering Blue / Green / Red
- normal core/situational purchases continue

V12 — CURRENT ITEM IMAGES

Data Dragon is still used for item metadata and as a fallback asset source, but the
app first requests item images from the local League Client game-data assets. This
means the displayed item art should match the League Client currently installed on
the PC.

If old images remain after upgrading from an older app version:
1. Start League Client.
2. Start Rift Build Assistant V12.
3. Click "Refresh Item Images".
4. The app clears its item-image caches and loads the current assets again.


V13 — ADAPTIVE FULL BUILD

The Live Build Assistant now shows the target full build immediately instead of
requiring the user to infer the final build from several separate sections.

The target contains:
- 1 boots slot
- 5 major item slots

The algorithm builds the target in this order:
1. already completed major items are preserved
2. stable CORE items are added
3. current threat-aware situational choices are added
4. remaining spaces are filled from the current enemy-composition baseline
5. profile fallback items fill any remaining empty slots

This means:
- minute 0: a full target is already visible
- early game: core stays mostly stable
- mid/late game: later situational slots can change as enemy items become visible
- completed items are preserved so the app does not casually imply selling them

The card source label explains why an item is present:
- BOOTS
- OWNED
- CORE
- ADAPTIVE
- BASELINE
- FALLBACK

NEXT PURCHASE SYNCHRONIZATION

After the jungle starter is handled, Next Purchase Assistant follows the first
missing item from the exact Adaptive Full Build shown above. Therefore the purchase
planner and the displayed full build no longer point at different targets.


V14 — GOLD COMPARISON NOTE

Riot's Live Client player list provides each player's position, inventory, level,
K/D/A and CS. The active-player endpoint additionally provides currentGold for the
active player.

It does not provide each other player's unspent current gold in the normal player
list. Therefore the right side uses:

  VISIBLE ITEM GOLD = current non-consumable inventory value

This is a symmetric comparison for both teams, but it is not identical to total
gold earned.

RIGHT SIDE COLORS
- GREEN = your team / lane has more visible item gold
- RED = your team / lane has less visible item gold
- GRAY = equal visible item gold

The center divider between the two application sides can be dragged to resize them.


V15 — GANK PRIORITY

The right side now ranks TOP, MID and BOT (ADC + SUPPORT together). The score tracks visible item-gold difference and recent trend, level and CS gaps, ally setup, enemy vulnerability and rescue risk.

Important: this is a macro recommendation. The Live Client data used here does not provide exact wave position, ward locations, hidden enemy-jungle location or every relevant cooldown. Always verify the actual lane position and minimap before committing.


V16 — ICON SIZES

Draft recommendation portraits are now approximately 44 px instead of the previous
full-size champion art.

Smaller champion rows such as Draft allies/enemies, Enemy Threats and lane comparison
use approximately 28 px icons.

Item icon sizing is unchanged.


V17 — JUNGLE COMPANION VISIBILITY

The Blue / Green / Red choice is only displayed while:
- Smite is detected
- Smite is still in its base state
- no jungle companion is detected in inventory

As soon as Gustwalker, Mosstomper or Scorchclaw is detected, the entire Jungle
Companion section is removed from the live layout.

If the item name changes during the quest, upgraded Smite is an additional signal
that the selection has already happened, so the section stays hidden.

V17 — SIMPLIFIED BUILD VIEW

The component purchase planner is no longer displayed.

The build-related live UI now focuses on:
- Adaptive Full Build
- Enemy Threats
- Situational Item Options
- the existing baseline/core context below

There are no "buy this component now" cards.

V17 — HORIZONTAL GANK PRIORITY

TOP, MID and BOT are rendered in three equal cards next to each other.

Each card keeps the most important information:
- score / priority / risk
- lane item-gold delta
- recent trend
- level delta
- CS delta
- up to two primary reasons
- one risk warning when relevant


V18 — SMOOTH REFRESH

The main source of the visible blinking was the old right-side renderer destroying
and recreating champion widgets every 2.5 seconds whenever KDA/CS/level changed.
V18 creates the team rows and lane-opportunity cards once, then only updates their
text, colors and image references in place.

The app also tolerates two short failed Live Client polls before clearing the live
view, which prevents a transient localhost API hiccup from flashing the whole app.

V18 — BUILD STABILITY

Build reactivity is configurable. The default 1.2-point margin means a new adaptive
item generally must beat the currently retained option by about 1.2 fit points before
it displaces it in the full build. This keeps the full build from bouncing between
items after minor enemy purchases.

V18 — POST-GAME

Local reports are stored under the app's history folder. Each game gets a JSON file,
and games.csv receives a compact row. No account credentials are used.


V19 — DRAFT PORTRAITS

Tier letters are no longer painted on top of champion images.
The portrait is clean. Existing tier information may still appear as normal text
beside a Draft recommendation.

V19 — FIVE ROLE GOLD TRACKING

The right panel contains:
- TOP
- JUNGLE
- MID
- ADC
- SUPPORT

The right side now has its own vertical scrollbar and mouse-wheel behavior.
Objectives & Events are placed after the role comparison table so SUPPORT is not
pushed below that section.

V19 — GANK PRIORITY LAYOUT

TOP, MID and BOT use a 3-column Tk grid with one uniform column group, so all cards
receive exactly the same width.

Rank color is visual priority only:
- #1 GREEN
- #2 ORANGE
- #3 RED

Risk/opportunity labels are still shown inside the cards but no longer override
the rank color.


V20 — RESPONSIVE FIT

The primary application view no longer uses any vertical scrollbar.

The layout is optimized around two responsive columns:
- LEFT: Draft / Live Build
- RIGHT: Team comparison / Gank Priority / five role rows / Objectives & Events

On Windows the application attempts to open maximized. On other platforms it uses
approximately 96% of screen width and 90% of screen height.

The divider adjusts with the window:
- narrower window -> close to 50 / 50
- normal desktop -> roughly 54 / 46
- wide desktop -> roughly the saved 57 / 43 split

The compact live mode remains enabled by default. During a live match it hides the
secondary Current Items / Enemy Threat / Baseline blocks so the decision-relevant
Full Build and Situational Options stay visible without scrolling.

RIGHT PANEL DENSITY

To keep all content visible:
- team summary is shorter
- Gank Priority sparklines are shorter
- TOP / JUNGLE / MID / ADC / SUPPORT rows are compact
- champion lane icons are capped at about 22 px
- the five recent Objective/Event entries are arranged in two columns

No data section is placed behind a vertical scrollbar.


V21 — DRAFT SYNERGY & MATCHUPS

Each Top Composition Fit now contains three layers:

1. TEAM COMPOSITION
   The existing model still checks damage balance, frontline, engage and CC.

2. SPECIFIC ALLY SYNERGY
   Example:
     Synergy: Yasuo, Orianna

   The app checks the allies that are currently visible in Champion Select.
   Explicit champion pairs from draft_relationships.json are supplemented by
   general rules such as engage + AoE follow-up and frontline + hypercarry.

3. SPECIFIC ENEMY MATCHUPS
   Example:
     GOOD VS: Jinx, Brand
     HARDER VS: Poppy, Morgana

   These names come only from currently visible enemy picks.

The relationship contribution is deliberately small. It can move two close draft
choices, but it does not override major composition problems such as having no AP
damage, no frontline or no engage.

EDITABLE DATA

draft_relationships.json contains, per candidate champion:
- synergyWith
- goodInto
- badInto

This is heuristic relationship data, not a live patch win-rate database. It can be
edited without changing the Python source.


V22 — ENEMY THREAT / ALLY CARRY RANKING

The right side ranks the top three visible carries for both teams.

The score uses:
- current visible inventory value
- K/D/A
- level
- CS

It is a transparent local heuristic, not an MMR value or win probability.

The #1 enemy threat gives a small extra weight to situational defensive/offensive
responses that specifically answer that champion's visible item profile.

The #1 ally carry gives that side a small Gank Priority bonus so the app can
recognize when protecting or snowballing an already strong teammate is valuable.

V22 — SMART BOOTS

If boots are not already owned:
- high physical / crit / attack-speed pressure can move Plated Steelcaps up
- high magic / CC pressure can move Mercury's Treads up
- otherwise the champion profile's normal boots remain the fallback

Once boots are bought they are preserved in the displayed full build.

V22 — COUNTER RESPONSE

A compact line above Situational Item Options explicitly calls out:
- high sustain -> anti-heal value
- armor stacking -> armor penetration / Black Cleaver value
- high magic -> MR value
- high physical -> armor value
- high crit -> anti-crit value
- high attack speed -> anti-basic-attack value

Bruiser profiles may surface Chempunk Chainsword when that item exists in the
current Riot item metadata and enemy sustain is high.

V22 — BUILD CONFIDENCE

The displayed percentage is RELATIVE HEURISTIC CONFIDENCE based on:
- threat-fit score
- separation from the alternative options
- primary enemy threat relevance

It is explicitly not a win-rate percentage.

V22 — DRAFT TEAM IDENTITY

Each recommendation now summarizes the resulting composition identity, such as:
- Dive
- Teamfight
- Pick
- Poke
- Protect / Scale

It also calls out visible weaknesses such as:
- low frontline
- low engage
- no visible AP / AD
- limited disengage / protection

V22 — DRAFT LOADOUT

draft_loadouts.json contains editable local presets for:
- runes
- summoner spells

The Draft Assistant shows the preset for the champion you have selected. If you have
not selected one yet, it shows the preset for the current #1 recommendation.

These are local heuristic presets, not a live patch win-rate feed.

V22 — OBJECTIVE FIGHT READINESS

The app shows:
  DRAGON FIGHT: FAVORABLE / CONTESTABLE / HIGH RISK
  BARON FIGHT: FAVORABLE / CONTESTABLE / HIGH RISK / LATER

The estimate uses visible inventory-value differences from the whole team plus the
lanes most relevant to that side of the map. It does not claim the objective is
currently alive or that vision/wave state is known.

V22 — GAME PHASE + GAME STATE

Game phase:
- EARLY: before 14:00
- MID: 14:00–27:59
- LATE: 28:00+

Late-game Gank Priority is deliberately reduced because isolated lane ganks become
more vulnerable to grouped collapses and objective tradeoffs.

The integrated Game State line combines:
- AHEAD / EVEN / BEHIND
- visible team item-gold delta
- strongest side
- primary enemy threat
- current best lane opportunity
- current build adaptation + confidence


V23 — DASHBOARD UI

The application now follows the dark dashboard concept: left sidebar, compact top status bar, metric cards and denser strategy panels.

Live Overview emphasizes game state, threat/carry ranking, gank priority, objective readiness, recent events and all five role comparisons.
Build Assistant emphasizes Adaptive Full Build and situational counter responses.
Draft Assistant emphasizes team/enemy picks, synergy, matchups, team identity and local rune/summoner presets.


V24 — GAME STATE CONFIDENCE

The confidence score measures whether the app has enough stable live information:
- visible players
- mapped roles
- established lane-history samples
- visible item rows

It is NOT a win probability.

V24 — MOMENTUM

Lane momentum uses roughly the recent 75–90 second change in visible item-value
difference. Team momentum uses roughly two minutes.

Labels:
- SURGING
- GAINING
- STABLE
- LOSING
- SLIDING

V24 — STRATEGIC MODE

SNOWBALL:
  Strong visible team advantage and/or positive momentum.
  The gank model slightly favors converting strong sides while still avoiding
  very high-risk plays.

STABLE:
  Normal balanced weighting.

COMEBACK:
  Significant visible deficit and/or negative momentum.
  High-risk rescue ganks are penalized more heavily, while salvageable lanes
  can still receive value.

V24 — CHAMPION-SPECIFIC GANK PROFILES

Profiles are deliberately small score adjustments layered on top of the common
lane-state model. They account for whether the selected jungler tends to prefer:
- early / mid / late ganking windows
- squishy targets
- lane setup
- scaling / lower early risk

The app still does not know exact wave position, ward state, hidden enemies or
complete health/mana information.

V24 — OBJECTIVE SETUP SCORE

Dragon / Baron display a 0–100 visible-data setup score.

Hover the objective label to see the components:
- whole-team visible item delta
- Jungle delta
- Mid delta
- BOT+SUPPORT for Dragon
- TOP for Baron

The score does not indicate objective spawn state.

V24 — WHAT CHANGED

A short line remains visible for 12 seconds when a meaningful strategic value changes:
- Game State
- Snowball/Stable/Comeback mode
- main enemy threat
- best gank lane
- strong side
- Adaptive Full Build

V24 — SMOOTH CHANGE FEEDBACK

Important numeric changes briefly flash:
- green when the value improved
- red when the value worsened

Only foreground colors change. Champion/item images and dashboard widgets remain
mounted, preserving the V18+ smooth-refresh behavior.


V25 — PERFORMANCE / NAVIGATION FIX

The main cause of occasional UI freezing was that Riot localhost HTTP reads were
performed synchronously inside Tkinter's event loop. If either local endpoint took
close to its timeout, Windows could not process a sidebar click until the request
returned.

V25 moves only the raw localhost reads to a daemon worker thread:
- Champion Select LCU GET
- Live Client Data API GET

All Tkinter widget access and rendering remains on the main UI thread.

The navigation layer was also changed:
- rapid clicks are debounced/coalesced
- the same selected view does not repack the layout
- only one sash position update is performed per navigation
- automatic responsive resizing is root-only and debounced
- a sidebar-selected ratio is temporarily protected from Configure events

WAITING STATE OPTIMIZATION

Previously, when no game or Champion Select was active, some empty frames could be
cleared and rebuilt every refresh cycle. V25 renders each idle state once and leaves
it mounted until the source state actually changes.

These changes preserve V24's smooth in-place live updates and image caching.


V26 — DRAFT CHAMPION POOL MANAGER

Settings no longer relies on Ctrl+Click selection to decide which champions are
active in Draft Assistant.

The Champion Pool section now has two lists:

AVAILABLE
  Supported recommendation profiles that are not currently in your pool.

MY POOL
  Champions currently considered by Draft Assistant.

Controls:
  Add →
  ← Remove
  Add All
  Reset

Double-click also moves a selected champion between the lists.

Only champions with a local draft recommendation profile appear here. Adding an
arbitrary League champion would require a corresponding draft profile so the
assistant has composition / engage / frontline / damage / matchup heuristics for it.


V27 — ALL CHAMPIONS

Settings > Draft Champion Pool > AVAILABLE is populated from Riot Data Dragon,
not only from draft_profiles.json.

Use Search champion... to filter the full list.

Curated champions keep their hand-tuned draft profile. If you intentionally add a
different champion to MY POOL, the app creates a conservative generic composition
profile from Riot tags and local champion traits. Generic profiles are less precise
than curated matchup profiles and are visibly described as generic in Draft reasons.

V27 — RIOT MATCH HISTORY SYNC

Open Game History and enter:
- Riot ID: GameName#TAG
- regional route
- Riot API key

Then press Sync All Available Matches.

The app:
1. resolves Riot ID to PUUID through ACCOUNT-V1
2. pages through Match-V5 match IDs
3. downloads match details that are not already stored
4. stores raw Riot match JSON under history/riot/
5. stores a compact searchable index in history/riot_index.json

The API key is not saved anywhere by Rift Build Assistant.

The first full backfill can take a long time because Riot API rate limits must be
respected. Later syncs are much faster because already-downloaded matches are
skipped.

"All available" means every match currently exposed to the account through Riot's
Match-V5 API. The app cannot guarantee that Riot exposes every match ever played
since account creation, and special/custom match-history policy may differ.

ROUTING

Use the regional Match-V5 route:
- EUROPE
- AMERICAS
- ASIA
- SEA

This is the regional routing value, not the platform shard name such as EUN1/EUW1.

SECURITY

Riot API key:
- is entered into the Game History window
- is held only in process memory while syncing
- is not written to settings.json, riot_account.json, history files or logs


V28 — RIGHT PANEL READABILITY

The most important right-side information is larger:
- champion names
- visible item gold
- level / KDA / CS
- TOP / JUNGLE / MID / ADC / SUPPORT
- lane gold delta
- STRONG / NEUTRAL / WEAK
- Gank Priority titles / metrics
- team visible-item totals and Team Delta

The LANE / POWER center column is slightly wider. No scrolling was reintroduced.


V29 — COMPACT OBJECTIVES

The old OBJECTIVES & EVENTS section was too large for the value it provided.

The live dashboard now shows only:

  OBJECTIVES   DRAGON 72/100 • FAVORABLE   BARON 48/100 • CONTESTABLE

This one-line bar sits immediately below Gank Priority and above the detailed
TOP / JUNGLE / MID / ADC / SUPPORT comparison.

Hover Dragon or Baron to see the existing detailed readiness breakdown.

The visual event log was removed. Riot Live Client events are still processed and
can still be retained in local post-game reports, so removing the live event list
does not discard the underlying session data.


V30 — INTEGRATED NAVIGATION

Game History and Settings are no longer separate popup/Toplevel windows.

The sidebar now has five true application pages:
- Live Overview
- Build Assistant
- Draft Assistant
- Game History
- Settings

The top status bar remains visible on every page.

GAME HISTORY PAGE

The integrated history page keeps:
- Riot ID
- regional route
- memory-only Riot API key
- Sync All Available Matches
- Cancel Sync
- progress/status
- search
- combined Riot + locally observed match table

Switching away from the page does not destroy it or interrupt an active Riot sync.

SETTINGS PAGE

The integrated Settings page keeps:
- live display toggles
- build reactivity
- icon sizes
- split width
- all-champion AVAILABLE search
- Add / Remove / Add Visible / Reset Curated
- Save Settings
- Reset Item Cache

Settings are now edited in place. Save Settings applies them without closing or
opening another window.

AUTO SWITCH

Champion Select / Live Game detection continues in the background, but Auto Switch
does not force the user out of Game History or Settings.


V31 — RANKED HISTORY SCOPE

Game History is now focused on the data that matters for ranked review.

CURRENT SEASON
  2026 Season 3
  Start: 2026-07-29 12:00 local server time

QUEUES
  420 — Ranked Solo/Duo
  440 — Ranked Flex

Game History contains no option for:
- Normal Draft
- Quickplay
- ARAM
- Arena
- custom games
- previous ranked seasons

Riot Match-V5 is filtered before details are downloaded using:
- queue
- startTime

This makes the first sync much smaller and faster than downloading every available
match on the account.

Existing older/non-ranked raw data from V27-V30 is not automatically deleted from
disk, but V31 does not display it in the ranked History page.

ranked_season.json

The current season definition is kept in ranked_season.json so the season start
can be updated later without redesigning the History UI.


V32 — GAME HISTORY DISPLAY FIX

V31 could successfully sync and save Riot matches but still show an empty table.
The cause was in the UI refresh code: the Source column had been removed from the
ranked-only table, but the Treeview row values still referenced a variable named
`source`. That raised a NameError during the post-sync refresh.

The Riot sync callback previously swallowed UI refresh exceptions, so the user saw
"Sync complete" even though the table failed to render.

V32 fixes both issues:
- the stale Source value was removed
- History refresh exceptions are surfaced in the sync status
- Get API Key opens https://developer.riotgames.com/ directly


V33 — GAME HISTORY / MATCH REVIEW

HISTORY LIST

The Game History page now uses a dark two-pane layout.

Left:
- current-season ranked match list
- green wins
- red losses
- Date / Result / Champion / KDA / CS / Time / Queue / Role
- season Games / Win Rate / Record / Most Played cards

Right:
- selected match summary
- final build
- full 10-player scoreboard
- stat-based Match Review

Clicking a row immediately loads the selected match into the right pane.

MATCH REVIEW

The review uses Riot Match-V5 data and can flag likely areas to inspect:
- excessive deaths / lost tempo
- low kill participation
- same-role gold deficit
- same-role CS/min deficit
- low relative vision contribution
- no control wards in longer jungle/support games
- objective-control deficit
- objective damage gap versus the enemy jungler

It can also recognize strengths such as:
- low deaths
- high kill participation
- same-role gold/farm advantage
- strong vision contribution
- first-blood involvement
- objective steals
- high team damage share

IMPORTANT:
This is intentionally presented as a stat-based review. Match-V5 alone cannot
reconstruct exact pathing, wave state, ward locations, teammate cooldowns, or
whether an individual death/engage was strategically correct. The red review
points are evidence-based places to inspect, not guaranteed mistakes.

Full scoreboard/review requires the raw match JSON saved by Sync Ranked in the
current app version.


V34 — PERSISTENT RIOT ID

Default Riot ID:
  Player#EUNE

Settings now contains:
  RIOT ACCOUNT
  Riot ID: GameName#TAG

The value is stored in settings.json and automatically populated on the Game
History page every time the application starts.

The Riot ID can still be edited directly on Game History. Starting Sync Ranked
with a changed Riot ID saves that value back to Settings as well.

The API key behavior has NOT changed:
- API key is memory-only
- API key is never written to settings.json
- API key is never written to riot_account.json


V35 — VERSION-INDEPENDENT USER DATA

Windows:
  %LOCALAPPDATA%\RiftBuildAssistant

Stored there:
  settings.json
  history\
  history\riot\
  history\riot_index.json
  history\riot_account.json
  cache\

Static app configuration such as profiles.json and draft_profiles.json still ships
beside the source file.

UPGRADING

V35 scans only a few safe/local locations for previous extracted versions:
  - the current app's parent folder
  - Downloads
  - Desktop

If it finds an older Rift Build Assistant folder, missing Settings / History /
cache data is merged into the persistent data folder. Older folders are not
deleted or modified.

After V35 establishes the persistent data folder, future versions can use the same
data directly instead of starting over.

RANKED DASHBOARD

The current-season Game History page now includes:
  SOLO RANK
  FLEX RANK
  RECORD
  WIN RATE
  LAST 10
  STREAK
  MOST PLAYED

The rank/LP snapshot is refreshed during Sync Ranked using the same temporary API
key. The API key itself remains memory-only and is never written to disk.

Champion performance summarizes the top three champions from the locally stored
current-season ranked history with:
  games
  win rate
  average K / D / A

MATCH DETAIL

Selecting a match now adds visual context:
  champion portrait
  final build item icons
  hover item names
  10-player scoreboard
  stat-based post-game review

The existing green WIN / red LOSS history styling is preserved.

RIOT PLATFORM

Settings > RIOT ACCOUNT now includes a platform selector.
Default:
  Riot ID: Player#EUNE
  Platform: EUN1

Match-V5 still uses the regional route (EUROPE for this account); rank/LP uses the
platform route.


V36 — COMPLETE RANKED COACH

This release completes the remaining personal-analysis features.

GAME HISTORY WORKSPACE

The History page now contains three top-level tabs:

  Matches
  Champion Performance
  Trends & Alerts

MATCHES

The selected match uses four detail tabs:

  Overview
  Scoreboard
  Analysis
  Build

Overview:
  KDA
  CS/min
  Kill Participation
  Gold
  team objective comparison
  same-role comparison

Scoreboard:
  all 10 players
  champion / role / KDA / CS / gold / champion damage / vision

Analysis:
  existing stat-based review
  likely review points
  strengths
  transparent analysis limitations

Build:
  final item icons
  hover item names
  match economy / damage / vision context

CHAMPION PERFORMANCE

Current-season ranked performance is aggregated per champion:

  Games
  Wins / Losses
  Win Rate
  Average K / D / A
  Average CS/min
  Average Kill Participation

Champions with at least five games receive a light personal-performance signal:
  >=55% WR positive
  <=45% WR negative

This is your own match-history performance, not a public champion tier list.

TRENDS & ALERTS

Recent form compares the newest 10 games with the previous 10 when both windows
have enough games.

Signals can include:

  win rate improving / declining
  deaths increasing / improving
  CS/min changing
  kill participation changing
  high-performing champion with >=5 games
  weak-performing champion with >=5 games

The Last 30 results strip shows wins and losses chronologically.

These are descriptive statistics. They are not MMR, Elo or a prediction.

PERSONAL COACH

A compact Personal Coach panel appears in the main Live / Build / Draft workspace.

It creates up to three focus goals from the most recent ranked games, for example:

  reduce deaths if recent deaths are high
  improve useful fight involvement if KP is low
  protect farm tempo if CS/min has fallen
  avoid forcing plays during a recent downswing
  champion-specific note when the current champion has enough season games
  preserve strengths when recent survival / KP / farm are already good

The coach is intentionally advisory. It does not automate decisions or claim
knowledge of hidden game state.

DATA MANAGEMENT

Settings now includes:

  Backup Data
  Restore Backup
  Export Ranked CSV

Backup:
  settings.json
  history/
  raw Riot Match-V5 data

Cache files are intentionally not required in a backup because they can be
re-downloaded.

Restore:
  validates ZIP paths
  creates a safety backup first
  replaces Settings + History
  refreshes the current application state after restore

CSV export includes:
  Date
  Result
  Champion
  Role
  Kills / Deaths / Assists
  CS
  Duration
  Queue
  Final Items
  Match ID

Persistent user data remains under:
  %LOCALAPPDATA%\RiftBuildAssistant

API keys remain memory-only and are never included in backup files.


V37 — HISTORY SCOPE FIX

V36 interpreted "current season" literally as Riot Ranked Season 3, which began
July 29, 2026. That is why an account could show only the games played since that
date even though the player considers the ongoing 2026 ranked climb one season.

V37 defaults to:

  2026 Ranked Year (S1-S3)
  Start: 2026-01-08 12:00 local server time

Optional scope:

  Current Season 3 only
  Start: 2026-07-29 12:00 local server time

Both scopes remain ranked-only:
  Ranked Solo/Duo
  Ranked Flex

Never included:
  Normal Draft
  Quickplay
  ARAM
  Arena
  custom games

When changing scope to 2026 Ranked Year, press Sync Ranked. Match-V5 ID requests
use the January 8 start time and paginate by 100 IDs until Riot returns the final
page. Already downloaded S3 matches are reused; only missing S1/S2 match details
need to be downloaded.

TRENDS & ALERTS V2

The Trends page now fills the available space with several complementary views:

Top cards:
  Last 10 Win Rate
  Last 10 Deaths
  Last 10 CS/min
  Last 10 Kill Participation

Form Windows:
  Last 10
  Last 20
  Last 30
  full selected scope

Each window includes:
  W/L
  Win Rate
  KDA
  average deaths
  CS/min
  Kill Participation when raw Match-V5 data is available

Last 10 vs Previous 10:
  explicit delta for Win Rate
  explicit delta for Deaths
  explicit delta for CS/min
  explicit delta for Kill Participation
  improving / declining / stable color signal

Last 30 Results:
  chronological green/red result strip

Bottom panels:
  Trend Alerts & Positives
  Recent Champion Form (last 20 games)

The trend system remains descriptive and does not attempt to invent MMR/Elo.


V38 — AUTO RUNE IMPORT

CHAMPION SELECT FLOW

When Champion Select detects your actually selected champion:

  1. Rift Build Assistant loads the local champion rune profile.
  2. RiftSense calculates the recommended rune profile internally.
  3. If automatic rune import is enabled in Settings, Recommended is imported once.
  4. The app creates or updates ONE editable League rune page:
       RiftSense - <Champion>
  5. The page is sent with current=true.
  6. Later visible enemy picks do not repeatedly rewrite the same rune setup.

The top Draft Assistant champion recommendation is NEVER auto-imported. A rune
page can only be written after the user's own champion is actually selected.

RUNE AUTOMATION UI

Game Assistant does not show rune automation controls or manual import buttons.
Automatic rune import is controlled only from Settings.

SETTINGS

Settings > General:

  Enable automatic rune import in Champion Select

Settings > RUNE IMPORT explains which managed page is written.

RUNE PROFILES

Editable file:

  rune_profiles.json

Current curated profiles include:

  Wukong
  Nocturne
  Jarvan IV
  Amumu
  Maokai
  Warwick
  Vi
  Jax
  Shen
  Nasus

Each profile can contain:

  recommended
  alternative

Each choice contains:

  label
  runes

Example syntax:

  Conqueror • Triumph • Legend: Alacrity • Last Stand |
  Magical Footwear • Cosmic Insight

Rune names are converted to IDs using the current Riot Data Dragon
runesReforged.json data loaded for the app's current patch.

RUNE VALIDATION

Before writing a page, V38 validates:

  exactly 4 primary runes
  exactly 2 secondary runes
  one primary rune from each primary-tree row
  secondary runes from two different non-keystone rows
  primary and secondary trees are different
  every rune name exists in the current Riot Data Dragon catalog

If a rune was renamed/removed by Riot, V38 refuses that import instead of writing
an invalid page.

STAT SHARDS

V38 reads the current League rune page and preserves the last three stat-shard
perk IDs when possible.

If they cannot be read, a conservative fallback shard set is used.

LCU WRITE SAFETY

All existing Champion Select reads remain local.

V38 adds a narrow write method that refuses every write endpoint except:

  /lol-perks/...

It does NOT write:

  champion picks
  champion bans
  queue actions
  chat
  summoner spells
  account credentials
  inventory
  purchases

The League Client API is an unsupported local Riot service. Riot can change these
endpoints without notice, so a future League Client patch may require an app fix.

PROFILE QUALITY

The included rune profiles are curated local recommendations, not claimed live
patch win-rate rankings. The app exposes an Alternative choice and the JSON file
is editable.


V39 — READABILITY

Default:
  Text size = LARGE

Text-size modes:
  COMPACT      = original/small sizing
  NORMAL       = +1 point
  LARGE        = +2 points (V39 default)
  EXTRA LARGE  = +3 points

Change it here:
  Settings > UI & BUILD TUNING > Text size (restart)

Restart Rift Build Assistant after changing Text size because widgets are created
with the selected font profile at startup.

The readability system now covers:
  sidebar/navigation
  top bar
  Draft Assistant
  rune recommendations/import status
  Build Assistant
  lane comparison
  Gank Priority
  Personal Coach
  Game History
  Match Detail tabs
  Champion Performance
  Trends & Alerts
  Settings
  Treeview rows/headings
  standard Tk Entry/Listbox/Text fonts
  tooltips/status labels

Layout changes:
  default window: 1600x900
  minimum window: 1200x700
  sidebar width: 178 px
  History rows: scaled from a 30 px base
  Scoreboard rows: scaled from a 25 px base

All V38 Auto Rune Import and V37 ranked-history/trend functionality is preserved.


V40 — LANE POWER ALIGNMENT

Previous layout:
  left side used pack(expand)
  center used fixed width
  right side used pack(expand)

Different champion names / metadata could make some rows visually drift.

V40 layout:
  column 0 = YOUR TEAM, weight 1
  column 1 = fixed 112 px LANE / POWER
  column 2 = ENEMY TEAM, weight 1

Columns 0 and 2 use the same Tk grid "uniform" group, so both sides always receive
equal width. The center X position is therefore identical for:

  TOP
  JUNGLE
  MID
  ADC
  SUPPORT

V40 — 1V1 VS YOU

The center box still means:
  ally in that role vs enemy in that role

The enemy cell color now means:
  YOU (active player) vs that enemy

GREEN:
  1V1: FAVORABLE
  visible-data model currently favors you

RED:
  1V1: RISKY
  visible-data model currently favors the enemy

NEUTRAL:
  1V1: CLOSE
  no clear visible-data advantage

The 1v1 estimate uses:
  visible item value
  level
  K/D/A
  CS
  the existing player-power heuristic

It is intentionally not a guaranteed duel prediction. It cannot reliably know:
  important spell cooldowns
  summoner-spell cooldowns
  current tactical positioning
  hidden nearby players
  fog-of-war information
  champion-specific mechanical outplays

Hover the enemy cell for the exact visible-data comparison.

All V39 readability, V38 rune-import and V37 ranked-history/trend features are
preserved.


V41 — COMPACT LANE TABLE

V40 added the 1v1 indicator as an extra text line. With LARGE text this made each
role row too tall, so the bottom ADC / SUPPORT rows could fall below the visible
dashboard area.

V41 uses a compact layout:

YOUR TEAM:
  line 1 = Champion + visible item gold
  line 2 = Level + K/D/A + CS

CENTER:
  line 1 = Role
  line 2 = visible item-gold delta
  line 3 = STRONG / NEUTRAL / WEAK

ENEMY TEAM:
  line 1 = visible item gold + Champion
  line 2 = 1V1 state + Level / K/D/A / CS

The 1v1 color meanings remain:
  GREEN = FAVORABLE for you
  RED = RISKY for you
  neutral = CLOSE

Tested in the LARGE readability mode:
  TOP     47 px
  JUNGLE  47 px
  MID     47 px
  ADC     47 px
  SUPPORT 47 px

All five rows remain mapped and visible in the normal Live Overview layout.

All V40 lane-power logic, V39 readability, V38 rune import, and ranked-history
features are preserved.


V42 — SETTINGS FIX

V41 had two separate problems:

1. save_settings() swallowed filesystem exceptions, so the UI could appear to
   save even if settings.json was not written.

2. save_integrated_settings() changed SETTINGS but only refreshed a small subset
   of the already-built UI. Several options therefore did not visibly change
   until later—or were overwritten by hard-coded dashboard layout ratios.

V42 fixes both.

PERSISTENCE

settings.json is written atomically:
  write settings.json.tmp
  replace settings.json

If the write fails, Settings reports SAVE FAILED instead of pretending it worked.

LIVE APPLY

The following now apply immediately:
  Smart compact mode
  Current Items visibility
  Enemy Threats visibility
  Baseline/Core visibility
  Game State / carry-threat visibility
  Dragon / Baron readiness visibility
  Auto rune import
  Build reactivity
  Champion icon size on next render
  Draft icon size on next draft render
  Left width (%)
  Text size
  Draft champion pool

TEXT SIZE

COMPACT / NORMAL / LARGE / EXTRA LARGE now use live named fonts. Existing
widgets resize in-place. No restart is required.

LEFT WIDTH

The old navigation code forced different hard-coded split ratios for Live,
Build and Draft. V42 uses Settings > Left width (%) on every navigation change.

AUTO-SAVE

Display/behavior checkboxes and UI/build tuning comboboxes save immediately.

Champion pool actions also save immediately:
  Add
  Remove
  Add Visible
  Reset Curated

The always-visible top-right Apply & Save button is useful for Riot ID edits and
as an explicit manual save.

All V41 compact lane rows, V40 1v1 colors, V38 rune import and ranked-history
features are preserved.


V43 — PERSISTENT PLAYER MEMORY

Persistent files:

  %LOCALAPPDATA%\RiftBuildAssistant\player_memory.json
  %LOCALAPPDATA%\RiftBuildAssistant\performance_history.json
  %LOCALAPPDATA%\RiftBuildAssistant\ai_reviews\

These files live outside the extracted v43 folder. Future v44/v50/v60 builds can
therefore reuse the same Player Memory.

PLAYER MEMORY PAGE

Open:

  Game History > Player Memory

The page shows:

  Games Analyzed
  Active Patterns
  Champions
  Last Updated
  Current Coaching Focus
  Current Strengths
  Long-Term Patterns

Long-Term Patterns include:

  Type
  Pattern
  Evidence
  Confidence

V43 does NOT connect to an AI/LLM yet.

The memory engine is deterministic. It derives structured evidence from stored
ranked Match-V5/history data so a future AI coach can receive reliable context
instead of treating old AI prose as fact.

CURRENT COACHING FOCUS

Examples of evidence-backed focus items:

  Reduce avoidable deaths
  Protect farm tempo
  Improve useful fight involvement
  Recent form is declining
  A champion's stored results need review

CURRENT STRENGTHS

Examples:

  Recent survival is strong
  Recent CS/min is strong
  Recent KP is strong
  Strong recent win rate
  A champion is performing well

LONG-TERM PATTERNS

V43 can detect patterns such as:

  losses contain substantially more deaths than wins
  winning games have higher CS/min
  KP differs materially between wins and losses
  last 10 WR differs strongly from previous 10
  deaths/farm are improving or declining
  champion WR is strong/weak with enough games
  a champion wins much more often with <=4 deaths than with >=6 deaths

Each pattern has:

  stable pattern ID
  category
  title
  observation
  evidence
  sample size
  confidence
  positive / warning direction

FORGET SELECTED PATTERN

Select a row under Long-Term Patterns and press:

  Forget Selected Pattern

That pattern ID is stored in forgotten_pattern_ids. Recalculate Memory will not
bring it back.

RESET MEMORY

Reset Memory deletes:

  player_memory.json
  performance_history.json
  ai_reviews\ contents

It DOES NOT delete raw Riot match history. Press Recalculate Memory later to
rebuild a fresh profile from those ranked games.

PERFORMANCE HISTORY

performance_history.json keeps compact memory snapshots when the source match
set changes. Duplicate refreshes do not create duplicate snapshots.

This allows a future coach to compare:

  old average deaths -> new average deaths
  old CS/min -> new CS/min
  old KP -> new KP
  old coaching focus -> new coaching focus
  old pattern IDs -> new pattern IDs

ACCOUNT ISOLATION

New V43 Riot match summaries include account_puuid.

Older V27-V42 rows did not. V43 records the current PUUID as the owner of those
legacy untagged rows. If the Riot ID is later changed, those old legacy rows are
not mixed into the new account's Player Memory.

BACKUP / RESTORE

Backup format 2 now includes:

  settings.json
  history\
  player_memory.json
  performance_history.json
  ai_reviews\

This keeps the long-term coaching profile portable in addition to the normal
version-independent LOCALAPPDATA persistence.

FUTURE AI

A future AI coach can read the structured fields:

  summary
  champions
  current_focus
  strengths
  patterns
  performance snapshots

without needing to retrain a model or start from zero.

All V42 Settings fixes, V41 compact Lane Power, V40 1v1 colors, V38 Rune Import
and ranked-history features are preserved.


V44 — LIVE UI TEXT CLEANUP

The Live Overview previously displayed the same information in several places:

  top metric cards
  GAME STATE text
  Phase / Strong side / Enemy threat / Best lane text
  Build adaptation text
  ALLY CARRIES / ENEMY THREATS text row
  Gank Priority summary sentence
  Lane / Power table

V44 keeps one visual owner for each type of information.

TOP METRIC CARDS

These remain the primary place for:

  Game State
  Main Enemy Threat
  Ally Carry
  Game Phase

The Game State card no longer repeats team item delta because TEAM Δ already
shows it directly below.

The Phase card no longer repeats team momentum because momentum has its own
compact line.

TEAM ECONOMY

The team-economy box remains the primary place for:

  your team's visible item value
  enemy team's visible item value
  TEAM Δ
  whole-game delta graph

Hover TEAM Δ for the visible-inventory / unspent-gold limitation.

MOMENTUM

The old multi-part status:

  Visible item economy • Team momentum ... • SNOWBALL MODE

is now simply:

  Momentum GAINING +750g / ~2 min

Strategy mode remains in the Game State card.

CHANGED

The old permanent WHAT CHANGED line has been replaced with a transient event:

  CHANGED • Best gank MID → BOT

It appears only when a meaningful state changes and disappears after 12 seconds.

BUILD ASSISTANT

The previous top area used separate lines for:

  connection
  Player
  Stats
  Enemies

V44 renders one line:

  YOU • Amumu • Lv 16 • 3/8/15 • 160 CS • 28:51

Enemy champions remain visible in Live Overview / Lane Power, so the extra enemy
name list is not needed on the left.

SITUATIONAL ITEMS

Visible threat summary is now compact:

  Threat profile • PHY HIGH • MAGIC HIGH • CRIT HIGH • AS HIGH • SUSTAIN MED

The detailed COUNTER RESPONSE value is still calculated and retained in the
internal live summary, but is no longer a separate permanent line.

Option-card reason text no longer repeats:

  Answers primary threat Yasuo

on all three cards. Full detailed reasons remain available in the option tooltip.

GANK PRIORITY

The section header now contains only the jungler-specific identity, for example:

  Amumu • AoE setup jungler; values lanes that can follow his crowd control

The actual lane recommendation remains inside each TOP / MID / BOT card.

All V43 Player Memory, V42 Settings fixes, V41 compact Lane Power, V40 1v1
enemy coloring and V38 Auto Rune Import functionality are preserved.


V45 — DARK DROPDOWNS

The previous dark ttk theme configured general field colors, but Windows can
still render ttk.Combobox readonly/disabled states with native light colors.

V45 explicitly styles every Combobox state:

  normal / readonly:
    dark input background
    light text
    dark arrow-button background
    light arrow
    accent border on focus

  disabled:
    muted dark background
    muted text and arrow

The opened popup list is a separate Tk Listbox, so V45 also configures:

  *TCombobox*Listbox.background
  *TCombobox*Listbox.foreground
  *TCombobox*Listbox.selectBackground
  *TCombobox*Listbox.selectForeground

Result:

  History > Scope no longer becomes white when idle.
  Settings dropdowns stay dark.
  Riot Platform dropdown stays dark.
  The actual opened option list also matches the dark application.

All V44 Cleaner Live UI, V43 Player Memory, V42 Settings persistence,
V41 compact Lane Power, V40 1v1 colors and V38 Rune Import features remain.


V46 — RIFTSENSE BRANDING

Product name:

  RiftSense

Tagline:

  Live Intelligence for League of Legends

The main source file is now:

  RiftSense.py

The old product name is retained only where backward compatibility requires it.

PERSISTENT USER DATA

RiftSense intentionally continues using:

  %LOCALAPPDATA%\RiftBuildAssistant

This is the legacy data path from earlier versions. Renaming that folder now
would risk splitting or losing existing:

  settings
  ranked match history
  Player Memory
  performance snapshots
  caches
  backups

A later installer/data-migration release can move the folder safely if desired.

RUNE PAGE MIGRATION

New/default managed rune page name:

  RiftSense

If the League client already contains the old managed page:

  Rift Build Assistant

RiftSense recognizes it and reuses/renames it instead of creating a duplicate.

The feature/page names remain descriptive:

  Live Overview
  Build Assistant
  Draft Assistant
  Game History
  Settings

Only the overall product identity changed.


V47 — SELECTED RIFTSENSE LOGO

Selected identity:

  white R
  yellow/orange S
  orange rift/lightning split
  dark RiftSense UI background

Assets:

  assets\riftsense_logo.png
  assets\riftsense_icon.png
  assets\riftsense.ico

The PNG logo is used in the sidebar.
The smaller PNG is used as the Tk/Windows window icon.
The ICO is included for the future Windows EXE build.


V48 — PRODUCT POLISH

The goal of V48 is not to add a large gameplay feature. It is a presentation,
usability and desktop-product pass before Windows EXE packaging.

VISUAL HIERARCHY

RiftSense now uses distinct action styles:

  Primary
  Ghost
  Danger

Inputs and comboboxes have consistent dark focus borders and disabled states.

GAME HISTORY

The ranked-sync area is now a single structured card:

  Riot ID
  Route
  Riot API Key
  Ranked Solo/Duo
  Ranked Flex
  Scope
  Platform
  Sync Ranked
  Cancel

The API-key label explicitly states SESSION ONLY.

Sync status has a visual state chip:

  READY
  SYNCING
  SYNCED
  API KEY
  RATE LIMITED
  ERROR
  CANCELLED

SETTINGS

Settings are split into:

  General
  Champion Pool

This avoids a vertically overloaded settings page and improves compatibility
with 1080p screens using Windows display scaling.

FIRST RUN

A new installation with no Riot ID opens a branded setup window.

Users can:

  enter Riot ID + platform and Save & Continue
  Skip for now

Existing users with a persisted Riot ID are automatically marked as already
configured, so the onboarding does not interrupt upgrades.

DARK DIALOGS

Normal application notices, warnings, errors and confirmations now use
RiftSense-native dark Toplevel dialogs rather than bright Windows message boxes.

A native Windows messagebox is retained only as an emergency fallback if the
application itself fails before the RiftSense UI can be created.

LIVE WAITING / OFFLINE STATES

When no live game exists, RiftSense no longer presents an empty dense scoreboard.
The right side keeps the important overview cards plus a clear waiting-state card.

During a short Live Client interruption:

  LIVE DATA INTERRUPTED
  Retry x/3
  Last stable view is preserved

If active-player mapping fails:

  PLAYER DETECTION FAILED

HIGH-DPI LAYOUT

RiftSense enables Windows DPI awareness on a best-effort basis.

For high-DPI 1080p layouts, an automatic dense mode removes secondary copy:

  dashboard card detail lines
  redundant momentum summary
  gank reason/warning body copy
  larger sparkline height

The actual primary values, objective readiness and all five lane rows remain.

Validation was run at:

  96 DPI  ~= 100%
  120 DPI ~= 125%
  144 DPI ~= 150%

No GitHub upload or release action is part of V48.


V49 — APPEARANCE

Settings path:

  Settings > General > UI & Build Tuning > Appearance

Available values:

  DARK
  LIGHT

Appearance is saved immediately and can be changed while RiftSense is running.

LIGHT MODE

Light mode changes the main workspace, cards, panels, tabs, inputs, dropdowns,
tables, status backgrounds and dialogs to a light palette.

The sidebar remains a dark branded rail in both appearances. This is deliberate:
the selected RiftSense mark contains a white R and reads best on a dark surface.

SIDEBAR ALIGNMENT

The brand area now uses a centered vertical hierarchy:

  RS logo
  RIFTSENSE
  V49
  LIVE INTELLIGENCE
  FOR LEAGUE OF LEGENDS

The sidebar is 214 px wide and all navigation buttons use the same horizontal
inset and vertical spacing.

No GitHub upload or release action is included in V49.


V50 — BUILD IDENTITY

RiftSense now separates two questions:

  1. What job does this champion need to perform for the current team?
  2. Which situational item best answers the enemy threat?

For Nocturne:

  ASSASSIN
    selected when allied frontline is already covered
    or when one frontliner exists and the enemy team has several squishy targets

  BRUISER
    selected when allied frontline is limited

Example composition:

  Nautilus
  Nocturne
  Vex
  Xayah
  Braum

Nautilus + Braum already cover frontline. RiftSense therefore treats Nocturne
as an assassin/carry rather than trying to make him another durability layer.

ASSASSIN SLOT RULE

Owned completed items are always preserved.

For new recommended slots, assassin mode allows at most one item classified as
a defensive damage item. It will not recommend three durability slots simply
because the enemy composition has mixed damage / crowd control.

The current assassin candidate pool includes offensive lethality/penetration
options plus a small number of situational safety choices.

FULL BUILD CARDS

All six Adaptive Full Build cards use:

  one grid row
  six uniform columns
  shared minimum row height

This prevents longer item/source text from making one border noticeably taller
or shorter than the others.

LANE / POWER PORTRAITS

The previous Lane / Power renderer capped portraits at 22 px.

V50 uses:

  default Champion icon size 28 -> Lane portrait 32 px

The lane portrait size is still derived from the existing Champion icon setting
and is capped to protect layout density.

No GitHub upload or release action is included in V50.


V51 — META CONSENSUS

PURPOSE

RiftSense no longer has to treat one local build profile or one public website
as the single source of truth.

For the currently selected / played Jungle champion, V51 can collect public
build/rune signals from:

  LoLalytics        30%
  U.GG              25%
  OP.GG             20%
  Mobalytics        15%
  League of Graphs  10%

The source weights form the META layer. They are not the final item weights.

FINAL ITEM RECOMMENDATION

Situational item options use:

  Meta consensus             35%
  Team role / composition    25%
  Enemy matchup / threats    20%
  Your saved ranked history  15%
  Current live state          5%

Hover a Situational Item confidence/fit line to see this breakdown.

TEAM ROLE HAS A SAFETY VETO

RiftSense first decides the job needed by the current composition.

Example:

  Nautilus
  Nocturne
  Vex
  Xayah
  Braum

Nautilus + Braum already cover frontline, so Nocturne can be classified as
ASSASSIN. A common bruiser meta core is therefore not allowed to silently turn
that build back into a third durability/frontline layer.

When allied frontline is limited, the same Nocturne can remain BRUISER and use
the relevant meta baseline.

RUNES

Meta rune pages are reconstructed from currently valid Riot Data Dragon rune
names/IDs and validated with the same structural checks used by Rune Import.

Rune candidates may come from:

  weighted Meta Consensus
  individual parsed sources
  local rune_profiles.json recommended profile
  local alternative profile

The final rune recommendation considers:

  meta support
  current ally/enemy composition
  local personal champion-history signal

The actually selected local champion is still the only champion that can
trigger automatic rune import. Draft recommendations never auto-pick champions,
ban champions or write a rune page for an unselected recommendation.

TIER SIGNAL

When a cached Meta Consensus contains a tier, Draft Assistant displays that
tier. If not, tier_data.json remains the offline fallback.

Tier contributes only a modest draft-score adjustment. It cannot outweigh a
clearly poor composition or matchup fit.

CACHE / REFRESH

Default refresh:

  24 hours

Configurable in:

  Settings > Meta

Available refresh intervals:

  6 / 12 / 24 / 48 / 72 hours

Only the current/selected champion is automatically refreshed. This avoids
hammering five websites for an entire champion pool whenever RiftSense opens.

Cache location:

  %LOCALAPPDATA%\RiftBuildAssistant\cache\meta_consensus\

Changing the enabled source set makes the old cache stale and schedules a new
background refresh.

PRIVACY / NETWORK

Meta-source requests contain only:

  champion slug
  fixed Jungle / rank filters in the configured public URL
  generic HTTP headers

RiftSense does NOT send these sites:

  Riot ID
  Riot API key
  League Client credentials
  local ranked history
  Player Memory
  Live Client payload
  team/enemy player identities

Only hardcoded HTTPS source hosts are accepted. Redirects to another host are
rejected.

FAILURE MODE

Public websites can change HTML, require JavaScript, rate-limit or block
automated requests.

A source failure does not break Draft / Build / Rune Import.

RiftSense uses:

  successful remaining sources
  existing fresh/stale cache where available
  local profiles as the final fallback

PERSONAL HISTORY

Personal item/rune signals are descriptive associations, not causal win-rate
claims. Item completion is correlated with game length and whether a game is
already going well.

For this reason the personal signal is:

  capped
  shrunk toward neutral
  limited to 15% of the item recommendation blend

A successful Ranked History sync clears the in-memory personal signal cache so
new games can be included immediately.

No GitHub upload or release action is included in V51.


PATCH AGE

Public-source weight is reduced when the parsed page is behind the Riot Data
Dragon patch currently loaded by RiftSense:

  same patch       100%
  one patch old     75%
  two patches old   45%
  older             20%
  patch unknown     65%

This protects the consensus during patch rollout windows where one website has
updated before another.


V52 — GENERAL PROFILE

GENERAL

The first sidebar item is now:

  General

It is RiftSense's long-term player/home view. Live Overview remains focused on
the match currently being played.

PROFILE SUMMARY

General displays:

  Riot ID
  platform
  last ranked sync
  current Solo/Duo rank
  current Flex rank
  tracked wins
  tracked losses
  selected-scope win rate
  Last 10 record
  current streak
  most-played champion
  Last 10 vs previous 10 form direction

RANKED PROGRESS

RiftSense now persists rank snapshots in:

  %LOCALAPPDATA%\RiftBuildAssistant\rank_progress.json

A point is recorded after a successful Riot ranked sync when Solo/Flex rank data
has changed.

With two or more Solo snapshots, the General graph uses actual Riot
tier/division/LP progression.

With fewer than two snapshots, General shows:

  PERFORMANCE TREND — ROLLING 10 WIN RATE

This fallback uses saved ranked Match-V5 history and is replaced automatically
once enough real rank snapshots exist.

PERSONAL COACH

Personal Coach has been removed from the Live Overview / Build Assistant column.

It now lives at the bottom of General and continues using the same evidence-based
local coaching logic and persistent Player Memory.

The move is visual/organizational only; the coaching calculations were not
weakened or replaced with generic tips.

BACKUP

rank_progress.json is included in RiftSense backup files and restored with the
rest of the persistent player data.

No GitHub upload or release action is included in V52.


v1 BETA — TIER LIST

SIDEBAR

RiftSense now includes:

  General
  Live Overview
  Build Assistant
  Draft Assistant
  Tier List
  Game History
  Settings

TIER LIST ROLES

The Tier List page has:

  TOP
  JUNGLE
  MID
  ADC
  SUPPORT

DISPLAY SOURCE

The current display source is LoLalytics role-specific Emerald+ / Ranked
Solo-Duo / Global tier data.

Each role is cached separately under:

  %LOCALAPPDATA%\RiftBuildAssistant\cache\role_tier_list.json

Default cache lifetime:

  12 hours

The page shows tier groups such as:

  S+
  S
  S-
  A+
  A
  A-
  B+
  B
  B-
  C+
  C

Each champion card can show:

  champion portrait
  source role rank
  tier
  win rate
  pick rate

The tooltip additionally includes:

  ban rate
  lane/role share
  source
  patch

DESIGN SEPARATION

Tier List is intentionally a display/reference page.

RiftSense Build Assistant and Draft Assistant do not blindly copy the displayed
tier list. Their recommendations continue to use Meta Consensus plus team
composition, matchups, personal history and live-state logic.

VERSION LABEL

The product UI now uses:

  v1 Beta

Future development iterations should keep this public-facing label until the
product is intentionally promoted to another release stage.

An internal monotonically increasing build number may still be used for update
ordering, but it is not displayed in the RiftSense interface.

No GitHub upload or release action is included in this build.


v1 BETA — GAME ASSISTANT

SIDEBAR

The previous separate items:

  Live Overview
  Build Assistant
  Draft Assistant

are now one item:

  Game Assistant

Game Assistant keeps the existing underlying views but chooses the useful
context automatically:

  Champion Select -> Draft Assistant content
  Live game       -> Live Overview + Build Assistant content
  Waiting         -> Live/Build waiting workspace

This removes redundant navigation without removing any of the existing logic.

SIDEBAR ICON ALIGNMENT

Sidebar icons and labels are now separate UI cells.

The icon cell has a fixed width, so text no longer shifts horizontally because
Unicode icons such as the gear, diamond and list glyph have different visual
widths.

ENEMY JUNGLE CS

Riot Live Client can expose a player with an empty `position` field. The old
fallback assigned unresolved players by list order, which could put the wrong
enemy into the JUNGLE row and therefore show that player's CS.

RiftSense now:

  1. detects the visible Smite summoner spell
  2. reserves that player for JUNGLE
  3. uses explicit Riot position values for the remaining roles
  4. uses array-order fallback only for still unresolved slots

The numeric CS value shown is Riot Live Client `scores.creepScore`.

No hidden jungle information is inferred or estimated.

No GitHub upload or release action is included in this build.


TIER LIST DISPLAY BUCKETS

RiftSense intentionally shows only:

  S+
  S
  A
  B
  C
  D

Examples of source normalization:

  S+ -> S+
  S  -> S
  S- -> S
  A+ -> A
  A  -> A
  A- -> A
  B+ -> B
  B- -> B
  C+ -> C
  C- -> C
  D+ -> D
  D- -> D

The exact source subtier remains available in the champion tooltip.

CHAMPION PORTRAITS

The previous Tier List icon prefetch stopped after 70 missing portraits. Roles
can contain more than 70 listed champions, so some entries could remain as
initials.

The beta now processes every missing portrait for the selected role using the
existing Riot Data Dragon icon cache/downloader. The downloads run outside the
Tk UI thread.

No GitHub upload or release action is included in this build.


EXACT RANK LP

General now presents the Solo/Duo rank in this form:

  GOLD II — 67 LP

rather than making the LP less visually prominent.

RANK REFRESH ORDER

When General is opened or Refresh Rank is pressed:

  1. RiftSense attempts to read current ranked stats from the local League Client.
  2. If valid Solo/Flex rank data is returned, the exact LP is saved and displayed.
  3. If the local ranked endpoint is unavailable, the last stored Riot API snapshot remains visible.

The local refresh does not require the temporary Riot developer API key used by
Ranked History sync.

General also displays the source/timestamp, for example:

  Rank LP: League Client • 16 Aug 2026 • 21:35:10

or:

  Rank LP: Riot API • 16 Aug 2026 • 20:12:44

No GitHub upload or release action is included in this build.


GAME HISTORY WORKSPACE

The large SYNC RANKED HISTORY credentials card has been removed from Game
History.

History now starts with a compact toolbar containing:

  Solo/Duo
  Flex
  history scope
  sync state
  Sync Ranked
  Cancel
  Sync Settings
  compact progress/status

This leaves substantially more vertical space for:

  Ranked Dashboard
  match list
  selected-match review
  Champion Performance
  Trends & Alerts
  Player Memory

SETTINGS > RIOT & SYNC

Account/sync configuration now lives in one dedicated Settings tab:

  Riot ID
  Platform
  Route
  Riot API Key
  Get API Key
  persistent data folder

Persistent:

  Riot ID
  Platform
  Route

Session-only:

  Riot API Key

The API key is held only in the running process and is not written to
settings.json, backups or logs.

No GitHub upload or release action is included in this build.


GAME HISTORY REDESIGN

The Matches workspace is now organized as:

  Ranked summary hero
  Matches / Champions / Trends / Player Memory
  Left: searchable match-card list
  Right: selected-match review

The card list initially renders 60 matches. Load More adds the next 60 without
losing the current selected match. Search/filter changes reset the list to the
first page automatically.

No GitHub upload or release action is included in this build.


HISTORY RESIZE PERFORMANCE

The redesigned match list uses many Tk widgets inside a Canvas. Previously the
Canvas `<Configure>` callback resized the embedded card frame immediately for
every pixel of a Panedwindow sash movement.

That caused every visible card and its nested labels/frames to recalculate
geometry repeatedly while the user was dragging the divider.

The beta now:

  moves the pane/viewport immediately
  stores the latest requested match-list width
  waits 110 ms after the last resize event
  applies the embedded card width once
  recalculates the Canvas scrollregion once after layout settles

The first History page also renders 30 cards instead of 60. Load More remains
available for the rest of the filtered history.

Headless regression test with 233 saved matches:

  96 DPI  • 20 rapid sash moves: ~0.07 s
  144 DPI • 20 rapid sash moves: ~0.11 s

No GitHub upload or release action is included in this build.


HISTORY MOCKUP MATCH

The History page now follows the visual hierarchy from the proposed redesign:

  GAME HISTORY                              Sync Ranked
  ranked scope / queues

  SOLO RANK | RECORD | WIN RATE | LAST 10 | STREAK

  Matches | Champions | Trends | Player Memory

  [compact match cards] | [larger Selected Match panel]

Each match card has a stable layout:

  portrait
  WIN / LOSS
  champion
  queue / role
  date
  KDA
  CS
  CS/min
  duration

The champion/result area uses fixed Grid columns so resizing the divider cannot
collapse it out of view.

Selected Match keeps:

  Overview
  Scoreboard
  Analysis
  Build

Overview prioritizes:

  KDA
  CS/min
  Kill Participation
  Gold
  Vision/min
  Objectives
  same-role comparison

No GitHub upload or release action is included in this build.


HISTORY REFERENCE DESIGN

The Matches workspace follows the supplied reference structure:

  GAME HISTORY                                      Sync Ranked | Settings

  SOLO / DUO | WINS | LOSSES | WIN RATE | LAST 10 | STREAK | MOST PLAYED

  Matches | Champions | Trends | Player Memory

  [ compact match feed ] | [ selected-match detail workspace ]

MATCH FEED

Each rendered match includes:

  result accent strip
  champion portrait
  WIN / LOSS
  champion
  Ranked Solo/Duo or Flex
  role
  date/time
  KDA
  CS
  CS/min
  duration

The card layout keeps fixed identity/stat columns so important information does
not disappear when the divider is made narrower.

SELECTED MATCH — OVERVIEW

Primary metrics:

  KDA
  CS/min
  Kill Participation
  Gold
  Vision/min

Objectives:

  Dragon
  Baron
  Rift Herald
  Towers

Same-role comparison:

  Gold delta
  CS/min delta
  Vision/min delta
  Objective Damage delta

The Role Edge gauge is a deterministic relative stat summary. It is not hidden
MMR, a win probability, or a replay/timeline claim.

NAVIGATION STABILITY

History maintains its already-built match-card widgets while the user navigates
to another RiftSense page and back.

A full rebuild is reserved for actual history changes, scope/queue changes,
Ranked sync completion or explicit data refreshes.

Search and Win/Loss filtering reuse the current row cache.

No GitHub upload or release action is included in this build.


HISTORY TARGET MATCH

This build specifically follows the supplied target screenshot rather than the
earlier loose interpretation.

TOP SUMMARY

  ranked crest
  Solo/Duo rank + LP
  Wins
  Losses
  Win Rate
  Last 10 with result blocks
  Streak
  Most Played + portrait

MATCH FEED

  search
  Solo/Duo chip
  Flex chip
  result filter
  scope menu
  result accent strip
  champion portrait
  champion
  queue
  colored K/D/A
  KDA ratio
  CS
  CS/min
  duration
  date/time
  match action

SELECTED MATCH

Tabs:

  Overview
  Scoreboard
  Analysis
  Build
  Vision

Overview:

  KDA + KDA ratio
  CS + CS/min
  KP
  Gold + gold/min
  Vision + vision/min
  objective cards
  ally vs enemy-role portrait comparison
  evidence-based match summary

NAVIGATION / PERFORMANCE

Game History retains already-rendered cards while navigating away and back.
Search/result filters reuse cached history rows. Divider resizing remains
debounced so nested match-card widgets do not relayout on every sash pixel.

No GitHub upload or release action is included in this build.


HISTORY VISUAL ASSETS

Rank crest assets:

  assets/history/ranks/

History navigation icons:

  assets/history/tabs/

Objective icons:

  assets/history/objectives/

CHAMPION PORTRAITS

History uses circular champion portraits in:

  match feed
  Most Played
  Selected Match
  Performance vs Enemy Role

The circular mask is generated at runtime with Tk PhotoImage transparency.
No Pillow/PIL dependency is required by RiftSense itself.

CUSTOM HISTORY TABS

The visible History tabs are now custom controls with:

  icon
  label
  flat dark surface
  gold selected text
  gold selected underline

The underlying ttk.Notebook tab headers are hidden.

OBJECTIVES

The Overview objective row now includes visual icons for:

  Dragon
  Baron
  Rift Herald
  Towers

No GitHub upload or release action is included in this build.


HISTORY DISPLAY-NAME NORMALIZATION

Riot / Data Dragon can expose internal identifiers that differ from the
player-facing champion name.

Example:

  MonkeyKing -> Wukong

RiftSense now keeps both values:

  raw identifier  -> icon / data lookup
  display name    -> user interface

HISTORY TOP SUMMARY

The ranked summary now uses responsive grid columns rather than left/right
packing. This prevents large unused gaps on wide desktop windows.

LAST 10

Result indicators are explicit pixel-sized bars:

  13 px wide
  6 px high
  2 px spacing

MATCH SUMMARY

The review text is larger and uses a wider wrapping area for better readability.

No GitHub upload or release action is included in this build.


REFRESH RANK

General > Refresh Rank uses this order:

  1. Riot League-V4, if a session Riot API key is present.
  2. Local League Client ranked stats as fallback.
  3. Keep the previous exact snapshot and show an explicit refresh error.

Refresh Rank does not download the whole match history.

When a fresh Solo/Duo snapshot is returned, General updates:

  Rank / LP
  Wins
  Losses
  Win Rate
  rank source + timestamp
  rank-progress snapshot

CURRENT ITEM VALIDATION

RiftSense now validates recommendation candidates against the loaded patch's
Data Dragon item metadata.

Rejected recommendation candidates include:

  non-purchasable entries
  items explicitly disabled on Summoner's Rift (map 11)
  hidden / non-store entries
  champion-specific shop entries
  consumables / trinkets
  non-boot components used as full-build slots

This validation applies after local profile/meta selection, so an old static
profile or stale third-party meta candidate cannot bypass the current patch's
item availability checks.

No GitHub upload or release action is included in this build.


API KEY / HISTORY AUTO-SYNC FLOW

  1. Open Settings > Riot & Sync.
  2. Paste the temporary Riot API key.
  3. Press Apply & Save.
  4. Open Game History.
  5. RiftSense starts one ranked-history sync automatically.

The key stays only in the running process.

The following are persisted:

  Riot ID
  Platform
  Regional route

The following is NOT persisted:

  Riot API key

Repeated navigation to Game History does not start another automatic sync unless
Apply & Save is used again with a session key.

The normal Sync Ranked button remains available for explicit manual refreshes.

No GitHub upload or release action is included in this build.


SUMMONER'S RIFT ITEM FILTER

Data Dragon contains a broad catalogue of League item data. A record being
present in item.json is not sufficient evidence that it is a normal Summoner's
Rift store item.

RiftSense now rejects recommendation candidates when they are:

  Arena / Prismatic special-distribution entries
  extended mode-only item IDs
  non-purchasable
  hidden / non-store
  explicitly disabled on map 11
  champion-specific
  consumables / trinkets
  normal components used as completed full-build slots

Example regression:

  Lightning Rod (Arena Prismatic item) -> BLOCKED
  Black Cleaver (normal SR item)       -> ALLOWED

Third-party meta pages are treated only as candidate sources. Every candidate
still has to pass RiftSense's current-SR item validator before it can appear in
a build.

No GitHub upload or release action is included in this build.


RANKED SYNC FLOW

With a temporary Riot API key:

  1. Open Settings > Riot & Sync.
  2. Enter Riot ID, Platform, Route and Riot API Key.
  3. Press Apply & Save.
  4. RiftSense starts the ranked sync immediately in the background.
  5. Watch SYNC STATUS in Settings or open Game History to see the same live status.
  6. New matches are rendered after the worker completes.

Visible sync phases include:

  Connecting to Riot API
  Account found
  Rank refreshed / rank warning
  Scanning ranked match IDs
  Matches found
  Downloading new match details
  Rate-limit wait
  Sync complete
  API-key / HTTP error
  Cancelled

The sync button cannot be started twice while a worker is active.

DATA SAFETY

The Riot API key remains in the shared in-memory StringVar only for the current
RiftSense process. It is not written to:

  settings.json
  riot_account.json
  backups
  logs

Riot ID, platform and regional route remain normal persistent preferences.

No GitHub upload or release action is included in this build.


RANKED SYNC IDENTITY FLOW

For a personal desktop installation, RiftSense no longer depends exclusively on
ACCOUNT-V1 to get the current player's PUUID.

Resolution order:

  saved PUUID for the same Riot ID
  League Client /lol-summoner/v1/current-summoner
  Riot ACCOUNT-V1 fallback

The local League Client request is read-only and localhost-only.

TEST API

Settings > Riot & Sync now includes Test API.

Possible results include:

  API TEST OK
  PUUID via League Client
  League-V4 HTTP 200
  Match-V5 HTTP 200

or a stage-specific error such as:

  ACCOUNT-V1 HTTP 403
  League-V4 HTTP 403
  Match-V5 HTTP 403

Test API does not save match history. It exists only to identify which stage
Riot accepts or rejects.

SECURITY

The Riot API key remains session-only and is not written to settings, account
snapshots, backups or logs.

No GitHub upload or release action is included in this build.


PRE-PUSH CHECK 1 — REAL RIOT SYNC

Use:

  Settings > Riot & Sync > Verify & Sync

The verifier checks:

  PUUID resolution
  League-V4 HTTP access
  Match-V5 match-list HTTP access
  Match-V5 match-detail HTTP access

If all stages pass, RiftSense starts the normal full ranked-history sync.

This is intentionally different from Test API:

  Test API       -> read-only endpoint diagnostic
  Verify & Sync  -> verifies the complete path, then starts the real sync

A true real-machine pass still has to be run on the installation that will be
used for release, because the build environment cannot access that machine's
League Client or session API key.

PRE-PUSH CHECK 2 — RECOMMENDATION ITEM AUDIT

In the app:

  Settings > Meta > Audit Recommended Items

Command line:

  python tools/pre_push_audit.py

The audit checks every upstream recommendation name from:

  profiles.json balanced/magic/physical paths
  profile boots
  adaptive item pools
  assassin pools and cores
  adaptive/threat-weight item tables
  cached Meta Consensus item candidates

Every candidate must pass the same current Summoner's Rift validator used by
live build rendering.

The command-line audit exits with code 1 when any invalid recommendation
candidate is found, making it suitable for a future CI/pre-release gate.

No GitHub upload or release action is included in this build.


IMMEDIATE BOOTS SLOT

Adaptive Full Build now guarantees:

  Slot 1 = boots
  Slots 2-6 = five non-boot completed items

Boot selection no longer depends on Data Dragon metadata being ready at the
exact first live-game poll.

If item data is temporarily unavailable:

  boot name is still shown
  slot 1 remains present
  placeholder says BOOT
  current-patch item id/icon is attached automatically after data recovery

PATCH DATA RECOVERY

The previous patch-health check returned early when:

  Data Dragon version == live client patch

even if item.json had failed to load.

The new check requires:

  matching patch version
  current item data loaded for that version
  current champion data loaded for that version

Missing item data retries on a short interval and forces build cards to rerender
as soon as it becomes available.

No GitHub upload or release action is included in this build.


GENERAL > SOLO RANK PROGRESS RANGE

The chart header now includes:

  7D
  30D
  90D
  1Y
  ALL

The selected range is persisted in settings.json.

Exact Solo/Duo rank history can only be graphed from snapshots RiftSense has
actually captured. Riot Match-V5 history does not contain the exact historical
LP/rank after every old match, so data from before RiftSense began recording
rank snapshots cannot be reconstructed accurately.

RiftSense now retains up to 2,000 changed-rank snapshots for long-term charts.

No GitHub upload or release action is included in this build.


RANK RANGE BEHAVIOR

Rank progress uses exact Riot rank snapshots captured by RiftSense.

Example:

  Stored LP snapshots: 16 Aug -> 22 Aug

Selecting 7D:
  the points occupy most of the recent seven-day window

Selecting 30D:
  the same exact points appear only in the final part of the 30-day window

Selecting 90D / 1Y:
  the recent data is compressed toward the right side because no older exact LP
  snapshots exist yet

Selecting ALL:
  the graph spans from the oldest saved snapshot to the newest

This is intentional. RiftSense does not invent historical LP before rank
tracking began.

No GitHub upload or release action is included in this build.


RELEASE READINESS

New Settings tab:

  Diagnostics

Diagnostics includes:

  Run Diagnostics
  Copy Diagnostics
  Run Pre-Release Check
  Open Logs
  Open Latest Log

Runtime logs:

  %LOCALAPPDATA%\RiftBuildAssistant\logs\riftsense.log

Logs rotate automatically and redact API-key-shaped values.

Crash handling:

  unexpected Tk callback errors are written to the log and shown in a
  RiftSense-native dialog with Copy Error and Open Logs actions.

Public source preparation now includes:

  README.md
  LICENSE
  SECURITY.md
  CHANGELOG.md
  CONTRIBUTING.md
  .gitignore

Release tools:

  python tools/pre_push_public_audit.py
  python tools/pre_push_audit.py
  python tools/run_release_checks.py

The public-source audit rejects local runtime data, logs, caches, compiled
Python output, API-key-shaped values and literal Windows user paths.

The only release gate that cannot be completed by an isolated build
environment is the real-machine Riot check:

  Settings > Riot & Sync > Verify & Sync

No GitHub upload or release action is included in this build.


RANKED LADDER GRAPH

General > Solo Rank Progress now uses a gaming-focused Ranked Ladder design:

  thin orange LP/rank progression line
  tier-tinted ladder background (Gold warm/yellow, Platinum cool/blue)
  rank/division background bands
  Current / Peak / Change / Win Rate / Games metrics
  promotion and demotion markers when exact saved rank snapshots cross a division
  selected-range Peak marker
  hover details on saved rank snapshots
  Match Results green/red dot strip
  7D / 30D / 90D / 1Y / ALL real-calendar range support

The Match Results strip shows results only. RiftSense does not invent historical
LP changes per match because Match-V5 does not provide old post-game LP values.


ADVANCED DRAFT ASSISTANT

Champion Pool is now role-specific:

  TOP
  JUNGLE
  MID
  ADC
  SUPPORT

Draft behavior:

  MY POOL is always preferred for the assigned role
  ROLE FALLBACK fills empty Top 3 slots only
  banned champions are excluded immediately
  already picked champions are excluded
  MIDDLE / BOTTOM / UTILITY normalize to Mid / ADC / Support
  active Champion Select polling uses an 800 ms refresh interval
  SAFE PICK / COUNTER PICK context is shown
  Draft Fit Confidence is shown as HIGH / MEDIUM / LOW
  confidence is draft-fit evidence, not game win probability
  picked and banned champions are excluded from recommendations
  Why this pick? opens detailed reasoning
  AUTOFILL / ROLE GAP warns when that role has no configured MY POOL
  POOL BLOCKED warns when all configured role champions are picked/banned

No pick, ban, or queue action is automated.
