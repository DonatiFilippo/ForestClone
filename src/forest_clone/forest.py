"""Rules that turn persisted focus sessions into forest trees."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


VALID_SPECIES = ("peach", "pine")
SAPLING_SECONDS = 30 * 60


@dataclass(frozen=True)
class TreeModel:
    species: str
    dead: bool
    sapling: bool
    scale: float
    session_id: int
    started_at: float
    duration_seconds: int
    elapsed_seconds: float
    ordinal: int
    total: int


def live_tree_count(duration_seconds: int) -> int:
    """One tree per hour chunk; final partial hour becomes a sapling."""
    if duration_seconds <= 3600:
        return 1
    full_hours, remainder = divmod(duration_seconds, 3600)
    return full_hours + int(remainder > 0)


def describe_tree_yield(duration_seconds: int, species: str) -> str:
    """Human-readable reward summary for overlays and desktop notifications."""
    name = "peach" if species == "peach" else "pine"
    if duration_seconds < 3600:
        kind = "sapling" if duration_seconds < SAPLING_SECONDS else "tree"
        return f"1 {name} {kind} planted"
    full_hours, remainder = divmod(duration_seconds, 3600)
    grown = f"{full_hours} grown {name} {'tree' if full_hours == 1 else 'trees'}"
    return f"{grown} and 1 {name} sapling planted" if remainder else f"{grown} planted"


def tree_scale(duration_seconds: float) -> float:
    """Readable bounded size curve from short sapling to four-hour tree."""
    duration = max(0.0, duration_seconds)
    if duration < SAPLING_SECONDS:
        return 0.48 + 0.12 * (duration / SAPLING_SECONDS)
    # 30 minutes starts at 65%; four hours reaches maximum size.
    return min(1.15, 0.65 + 0.5 * ((duration - SAPLING_SECONDS) / (4 * 3600 - SAPLING_SECONDS)))


def trees_for_session(session: Mapping[str, Any]) -> list[TreeModel]:
    status = str(session["status"])
    if status not in ("completed", "interrupted"):
        return []
    duration = int(session["duration_seconds"])
    species = str(session["tree_type"]) if "tree_type" in session.keys() else "peach"
    if species not in VALID_SPECIES:
        species = "peach"
    session_id = int(session["id"]) if "id" in session.keys() else 0
    started_at = float(session["started_at"]) if "started_at" in session.keys() else 0.0

    if status == "interrupted":
        elapsed = max(0.0, duration - float(session["remaining_seconds"]))
        return [
            TreeModel(
                species=species,
                dead=True,
                sapling=elapsed < SAPLING_SECONDS,
                scale=tree_scale(elapsed),
                session_id=session_id,
                started_at=started_at,
                duration_seconds=duration,
                elapsed_seconds=elapsed,
                ordinal=1,
                total=1,
            )
        ]

    if duration < 3600:
        return [
            TreeModel(
                species=species,
                dead=False,
                sapling=duration < SAPLING_SECONDS,
                scale=tree_scale(duration),
                session_id=session_id,
                started_at=started_at,
                duration_seconds=duration,
                elapsed_seconds=duration,
                ordinal=1,
                total=1,
            )
        ]

    full_hours, remainder = divmod(duration, 3600)
    total = full_hours + int(remainder > 0)
    trees = [
        TreeModel(
            species=species,
            dead=False,
            sapling=False,
            scale=tree_scale(duration),
            session_id=session_id,
            started_at=started_at,
            duration_seconds=duration,
            elapsed_seconds=duration,
            ordinal=ordinal,
            total=total,
        )
        for ordinal in range(1, full_hours + 1)
    ]
    if remainder:
        trees.append(
            TreeModel(
                species=species,
                dead=False,
                sapling=True,
                scale=min(0.60, tree_scale(remainder)),
                session_id=session_id,
                started_at=started_at,
                duration_seconds=duration,
                elapsed_seconds=duration,
                ordinal=total,
                total=total,
            )
        )
    return trees
