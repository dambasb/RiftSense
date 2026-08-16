# RiftSense

**Live Intelligence for League of Legends**

RiftSense is a desktop companion for League of Legends focused on live game awareness, build adaptation, draft assistance, jungle decision support, ranked analysis, and long-term player trends.

## Current status

RiftSense is currently in **pre-1.0 / beta development**. The core application is functional, while the UI, Windows packaging, updater, and release workflow are still being polished.

## Features

- Live Overview with game state, team item economy, momentum, enemy threats, ally carry, objective readiness, lane power, and 1v1 estimates
- Adaptive Build Assistant based on visible enemy itemization and team composition
- Draft Assistant with champion recommendations and curated rune profiles
- Optional managed rune-page import through the local League Client API
- Ranked Match History for Solo/Duo and Flex
- Champion performance, trends, alerts, and stat-based match review
- Persistent Player Memory built from saved ranked history
- Backup / restore and CSV export
- Dark desktop UI with configurable sizing and layout

## Privacy and data

RiftSense stores user settings, ranked history, caches, and Player Memory locally on the computer. Riot API keys are session-only and are not intended to be stored in the repository or bundled into releases.

## Requirements

For the source version:

- Windows
- Python 3.11+
- League of Legends / Riot Client for live-client and champion-select features

The current application uses the Python standard library only.

## Run from source

```bash
python RiftSense.py
```

## Project structure

```text
RiftSense.py
assets/
profiles.json
traits.json
draft_profiles.json
draft_relationships.json
draft_loadouts.json
rune_profiles.json
ranked_season.json
tier_data.json
```

## Planned before 1.0

- Final visual polish
- Windows `.exe` / installer
- Built-in update notification using GitHub Releases
- Application logging and better crash diagnostics
- Safer data/schema migrations
- Release automation

## Disclaimer

RiftSense is an independent community project and is not affiliated with or endorsed by Riot Games.
