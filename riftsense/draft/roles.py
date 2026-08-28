from __future__ import annotations

ROLE_KEY_MAP = {
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MID",
    "MID": "MID",
    "BOTTOM": "ADC",
    "ADC": "ADC",
    "UTILITY": "SUPPORT",
    "SUPPORT": "SUPPORT",
}
ROLE_KEYS = ("TOP", "JUNGLE", "MID", "ADC", "SUPPORT")


def canonical_role(value: str | None) -> str:
    return ROLE_KEY_MAP.get(str(value or "").strip().upper(), "UNKNOWN")


def role_display(role_key: str | None) -> str:
    return {
        "TOP": "Top",
        "JUNGLE": "Jungle",
        "MID": "Mid",
        "ADC": "ADC",
        "SUPPORT": "Support",
    }.get(str(role_key or "").upper(), "Unknown")
