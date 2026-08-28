# Security Policy

## Supported version

RiftSense is currently a **v1 Beta** project. Security fixes are applied to the
latest beta build.

## Reporting a vulnerability

Do **not** paste Riot API keys, League Client credentials, access tokens, PUUIDs,
private logs, or other secrets into a public GitHub issue.

If GitHub Private Vulnerability Reporting is enabled for the repository, use
that channel. Otherwise, open a public issue containing only a non-sensitive
description and state that additional private details are available.

## Local credentials

RiftSense may read the League Client lockfile from the local machine while the
client is running. Those credentials are used only for localhost League Client
requests.

The Riot Developer API key is session-only. RiftSense does not intentionally
write it to settings, backups, diagnostics, or logs.

## Logging

Runtime logs are stored outside the source directory under the user's local
RiftSense data folder. Logs use automatic token redaction. Before sharing a log,
review it for any information you do not want to disclose.

## Competitive integrity

RiftSense does not read League process memory, inject DLLs, automate combat,
movement, picks, bans, or queue actions. Rune automation is limited to a
managed rune page through local League Client endpoints.

## Network allowlists

Public Riot API requests are accepted only for HTTPS hosts ending in
`*.api.riotgames.com`, and redirect destinations are checked again. League
Client and Live Client traffic is restricted to localhost. LCU writes are
limited to `POST`/`PUT` requests under `/lol-perks/`.

Rune-page imports manage one editable page whose display name follows the
selected champion, for example `RiftSense - Nocturne`. RiftSense does not use
that write path for picks, bans, queue actions, chat, or gameplay automation.
