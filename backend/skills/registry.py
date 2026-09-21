"""Fixed V1 skill registry with no discovery or autonomous routing."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class SkillAsset:
    name: str
    version: str
    instructions: str


_SKILL_PATHS = {
    "query-generation": Path(__file__).parent / "query-generation" / "SKILL.md",
    "query-repair": Path(__file__).parent / "query-repair" / "SKILL.md",
    "mysql-query-generation": Path(__file__).parent / "mysql-query-generation" / "SKILL.md",
    "mysql-query-repair": Path(__file__).parent / "mysql-query-repair" / "SKILL.md",
}


@lru_cache
def get_skill(name: str) -> SkillAsset:
    try:
        path = _SKILL_PATHS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown static skill: {name}") from exc
    instructions = path.read_text(encoding="utf-8")
    return SkillAsset(name=name, version="v1", instructions=instructions)
