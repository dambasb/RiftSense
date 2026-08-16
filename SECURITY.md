# Security

## Reporting a security issue

Please avoid posting sensitive security reports, Riot API keys, local League Client credentials, or personal account data in public issues.

For now, security reports can be sent privately to the repository owner through GitHub profile contact information.

## Data handling

RiftSense is designed to keep application settings, ranked history, caches, and Player Memory on the local computer. Riot API keys should remain session-only and must not be committed to this repository.

## Local Riot interfaces

RiftSense communicates with Riot's local Live Client / League Client interfaces only through localhost. The application does not require Riot account passwords.

Managed League Client writes are intentionally restricted to the RiftSense rune page functionality; the application does not automate picks, bans, queue actions, or gameplay.
