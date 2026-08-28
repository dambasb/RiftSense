# RiftSense Architecture

RiftSense v1 Beta is being migrated from its original single-file prototype into a layered desktop application while preserving the stable `RiftSense.py` entrypoint and existing user data.

## Extracted layers

- `riftsense/core/storage.py` — JSON loading and atomic persistence.
- `riftsense/core/security.py` — Riot public-host and localhost-only URL policies.
- `riftsense/core/models.py` — typed dataclasses at structured data boundaries.
- `riftsense/riot/http.py` — whitelist-enforced Riot public API client.
- `riftsense/riot/local_client.py` — lockfile/LCU client, rune-page-only writes, and Live Client reads.
- `riftsense/draft/roles.py` — canonical role mapping.
- `tests/` — stdlib regression/security tests.

`RiftSense.py` remains the Tkinter composition/UI root during v1 Beta so refactors can be regression-tested without changing persistent data or user workflows. New non-UI network/storage/security logic should be added under `riftsense/`.

## Security boundaries

Public Riot API requests accept HTTPS only to `*.api.riotgames.com`, with redirect destinations revalidated. League Client traffic is localhost-only. LCU writes are restricted to POST/PUT under `/lol-perks/`; picks, bans, queue actions and chat remain impossible through the client wrapper.
