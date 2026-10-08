from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class IdentityDecision(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"


class IdentityStrength(str, Enum):
    PUUID = "PUUID"
    SESSION = "AUTHORITATIVE_SESSION"
    RIOT_ID = "RIOT_ID"
    WEAK_NAME = "WEAK_NAME"
    NONE = "NONE"


@dataclass(frozen=True)
class IdentityResolution:
    decision: IdentityDecision
    strength: IdentityStrength
    reason: str
    candidate: Mapping[str, Any] | None = None

    @property
    def matched(self) -> bool:
        return self.decision is IdentityDecision.MATCH


def _text(value: Any) -> str:
    return str(value or "").strip()


def _name_key(value: Any) -> str:
    """Conservatively normalize human-facing Riot names.

    Riot names are compared case-insensitively with surrounding whitespace
    ignored. Unicode and punctuation are otherwise left untouched; RiftSense
    does not invent equivalences Riot has not guaranteed.
    """
    return _text(value).casefold()


def _complete_riot_id(value: Any) -> tuple[str, str] | None:
    raw = _text(value)
    if "#" not in raw:
        return None
    game_name, tag_line = raw.rsplit("#", 1)
    game_key = _name_key(game_name)
    tag_key = _name_key(tag_line)
    if not game_key or not tag_key:
        return None
    return game_key, tag_key


def _identity_fields(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, Mapping) else {}
    puuid = _text(payload.get("puuid"))

    riot_id = _complete_riot_id(payload.get("riotId"))
    game_name = _text(payload.get("gameName") or payload.get("riotIdGameName"))
    tag_line = _text(
        payload.get("tagLine")
        or payload.get("riotIdTagLine")
        or payload.get("riotIdTagline")
    )
    if riot_id is None and game_name and tag_line:
        riot_id = (_name_key(game_name), _name_key(tag_line))

    weak_names = {
        _name_key(value)
        for value in (
            payload.get("summonerName"),
            payload.get("displayName"),
            game_name,
            riot_id[0] if riot_id is not None else "",
            payload.get("riotId") if riot_id is None else "",
        )
        if _name_key(value)
    }
    return {
        "puuid": puuid,
        "riot_id": riot_id,
        "weak_names": weak_names,
    }


def resolve_player_identity(
    reference: Mapping[str, Any] | None,
    candidates: Iterable[Mapping[str, Any]],
    *,
    allow_weak: bool = True,
) -> IdentityResolution:
    """Resolve one player without allowing weak evidence to beat strong data."""
    candidate_list = [candidate for candidate in candidates if isinstance(candidate, Mapping)]
    ref = _identity_fields(reference)
    fields = [_identity_fields(candidate) for candidate in candidate_list]

    if ref["puuid"]:
        puuid_matches = [
            index for index, item in enumerate(fields)
            if item["puuid"] == ref["puuid"]
        ]
        if len(puuid_matches) == 1:
            return IdentityResolution(
                IdentityDecision.MATCH,
                IdentityStrength.PUUID,
                "PUUID_EXACT",
                candidate_list[puuid_matches[0]],
            )
        if len(puuid_matches) > 1:
            return IdentityResolution(
                IdentityDecision.AMBIGUOUS,
                IdentityStrength.PUUID,
                "DUPLICATE_PUUID",
            )
        if any(item["puuid"] for item in fields):
            return IdentityResolution(
                IdentityDecision.NO_MATCH,
                IdentityStrength.PUUID,
                "PUUID_CONFLICT",
            )

    if ref["riot_id"]:
        riot_id_matches = [
            index for index, item in enumerate(fields)
            if item["riot_id"] == ref["riot_id"]
        ]
        if len(riot_id_matches) == 1:
            return IdentityResolution(
                IdentityDecision.MATCH,
                IdentityStrength.RIOT_ID,
                "RIOT_ID_EXACT",
                candidate_list[riot_id_matches[0]],
            )
        if len(riot_id_matches) > 1:
            return IdentityResolution(
                IdentityDecision.AMBIGUOUS,
                IdentityStrength.RIOT_ID,
                "DUPLICATE_RIOT_ID",
            )
        if any(item["riot_id"] for item in fields):
            return IdentityResolution(
                IdentityDecision.NO_MATCH,
                IdentityStrength.RIOT_ID,
                "RIOT_ID_CONFLICT",
            )

    if allow_weak and ref["weak_names"]:
        weak_matches = [
            index for index, item in enumerate(fields)
            if ref["weak_names"] & item["weak_names"]
        ]
        if len(weak_matches) == 1:
            return IdentityResolution(
                IdentityDecision.MATCH,
                IdentityStrength.WEAK_NAME,
                "UNIQUE_WEAK_NAME",
                candidate_list[weak_matches[0]],
            )
        if len(weak_matches) > 1:
            return IdentityResolution(
                IdentityDecision.AMBIGUOUS,
                IdentityStrength.WEAK_NAME,
                "MULTIPLE_WEAK_NAME_MATCHES",
            )

    return IdentityResolution(
        IdentityDecision.NO_MATCH,
        IdentityStrength.NONE,
        "NO_TRUSTWORTHY_MATCH",
    )


def resolve_champion_select_player(
    session: Mapping[str, Any] | None,
) -> IdentityResolution:
    """Resolve the local Champion Select entry by its authoritative cell ID."""
    if not isinstance(session, Mapping):
        return IdentityResolution(
            IdentityDecision.NO_MATCH,
            IdentityStrength.NONE,
            "NO_CHAMP_SELECT_SESSION",
        )
    local_cell = session.get("localPlayerCellId")
    if local_cell is None or isinstance(local_cell, bool):
        return IdentityResolution(
            IdentityDecision.NO_MATCH,
            IdentityStrength.NONE,
            "NO_LOCAL_PLAYER_CELL",
        )
    matches = [
        entry
        for entry in (session.get("myTeam") or [])
        if isinstance(entry, Mapping) and entry.get("cellId") == local_cell
    ]
    if len(matches) == 1:
        return IdentityResolution(
            IdentityDecision.MATCH,
            IdentityStrength.SESSION,
            "LOCAL_PLAYER_CELL_EXACT",
            matches[0],
        )
    if len(matches) > 1:
        return IdentityResolution(
            IdentityDecision.AMBIGUOUS,
            IdentityStrength.SESSION,
            "DUPLICATE_LOCAL_PLAYER_CELL",
        )
    return IdentityResolution(
        IdentityDecision.NO_MATCH,
        IdentityStrength.SESSION,
        "LOCAL_PLAYER_CELL_NOT_FOUND",
    )
