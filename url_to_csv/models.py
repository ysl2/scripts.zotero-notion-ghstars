from dataclasses import dataclass
from pathlib import Path

from shared.papers import PaperSeed


@dataclass(frozen=True)
class FetchedSeedsResult:
    seeds: list[PaperSeed]
    csv_path: Path
