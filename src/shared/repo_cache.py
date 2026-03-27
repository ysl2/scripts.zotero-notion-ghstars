import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RepoCacheEntry:
    arxiv_url: str
    github_url: str | None
    hf_exact_no_repo_count: int
    created_at: str
    updated_at: str
    last_hf_exact_checked_at: str | None


class RepoCacheStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        self.connection.close()

    def get(self, arxiv_url: str) -> RepoCacheEntry | None:
        row = self.connection.execute(
            """
            SELECT arxiv_url, github_url, hf_exact_no_repo_count, created_at, updated_at, last_hf_exact_checked_at
            FROM repo_cache
            WHERE arxiv_url = ?
            """,
            (arxiv_url,),
        ).fetchone()
        if row is None:
            return None

        return RepoCacheEntry(
            arxiv_url=row["arxiv_url"],
            github_url=row["github_url"],
            hf_exact_no_repo_count=row["hf_exact_no_repo_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_hf_exact_checked_at=row["last_hf_exact_checked_at"],
        )

    def record_found_repo(self, arxiv_url: str, github_url: str) -> None:
        now = _utc_now()
        self.connection.execute(
            """
            INSERT INTO repo_cache (
                arxiv_url,
                github_url,
                hf_exact_no_repo_count,
                created_at,
                updated_at,
                last_hf_exact_checked_at
            )
            VALUES (?, ?, 0, ?, ?, ?)
            ON CONFLICT(arxiv_url) DO UPDATE SET
                github_url = excluded.github_url,
                hf_exact_no_repo_count = 0,
                updated_at = excluded.updated_at,
                last_hf_exact_checked_at = excluded.last_hf_exact_checked_at
            """,
            (arxiv_url, github_url, now, now, now),
        )
        self.connection.commit()

    def record_exact_no_repo(self, arxiv_url: str) -> None:
        now = _utc_now()
        self.connection.execute(
            """
            INSERT INTO repo_cache (
                arxiv_url,
                github_url,
                hf_exact_no_repo_count,
                created_at,
                updated_at,
                last_hf_exact_checked_at
            )
            VALUES (?, NULL, 1, ?, ?, ?)
            ON CONFLICT(arxiv_url) DO UPDATE SET
                hf_exact_no_repo_count = CASE
                    WHEN repo_cache.github_url IS NULL THEN repo_cache.hf_exact_no_repo_count + 1
                    ELSE repo_cache.hf_exact_no_repo_count
                END,
                updated_at = excluded.updated_at,
                last_hf_exact_checked_at = excluded.last_hf_exact_checked_at
            """,
            (arxiv_url, now, now, now),
        )
        self.connection.commit()

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS repo_cache (
                arxiv_url TEXT PRIMARY KEY,
                github_url TEXT,
                hf_exact_no_repo_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_hf_exact_checked_at TEXT
            )
            """
        )
        self.connection.commit()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
