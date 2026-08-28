from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class RankEntry:
    tier: str = ""
    division: str = ""
    league_points: int = 0
    wins: int = 0
    losses: int = 0

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "RankEntry":
        value = value or {}
        return cls(
            tier=str(value.get("tier", "") or "").upper(),
            division=str(value.get("rank", "") or "").upper(),
            league_points=int(value.get("league_points", 0) or 0),
            wins=int(value.get("wins", 0) or 0),
            losses=int(value.get("losses", 0) or 0),
        )


@dataclass(slots=True)
class DraftSuggestion:
    score: float
    champion: str
    reasons: list[str] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    relationships: dict[str, Any] = field(default_factory=dict)

    def as_tuple(self) -> tuple[float, str, list[str], dict[str, Any], dict[str, Any]]:
        return self.score, self.champion, self.reasons, self.profile, self.relationships

    def __iter__(self) -> Iterator[Any]:
        return iter(self.as_tuple())

    def __getitem__(self, index: int) -> Any:
        return self.as_tuple()[index]
