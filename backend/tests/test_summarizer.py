import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.database import init_db
from app.summarizer import ensure_cluster_summary


class SummaryCacheTests(unittest.TestCase):
    def setUp(self):
        self.database_path = (
            Path(__file__).parent / f".test-summary-{uuid4().hex}.db"
        )
        self.database_patch = patch(
            "app.database.DATABASE_PATH",
            self.database_path,
        )
        self.database_patch.start()
        init_db()

    def tearDown(self):
        self.database_patch.stop()
        if self.database_path.exists():
            self.database_path.unlink()

    def _insert_cluster(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            cursor = connection.execute(
                """
                INSERT INTO clusters (
                    label, started_at, ended_at, article_count,
                    centroid, created_at, updated_at
                )
                VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    "Major earthquake hits coast",
                    "2026-06-21T10:00:00+00:00",
                    "2026-06-21T10:00:00+00:00",
                    "[]",
                    "2026-06-21T10:00:00+00:00",
                    "2026-06-21T11:00:00+00:00",
                ),
            )
            connection.commit()
            return cursor.lastrowid

    def _insert_summary(self, cluster_id, content, updated_at):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO summaries (
                    cluster_id, model, content, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    cluster_id,
                    "gpt-5.5",
                    content,
                    "2026-06-21T10:30:00+00:00",
                    updated_at,
                ),
            )
            connection.commit()

    def _cluster(self, cluster_id, updated_at="2026-06-21T11:00:00+00:00"):
        return {
            "id": cluster_id,
            "label": "Major earthquake hits coast",
            "started_at": "2026-06-21T10:00:00+00:00",
            "ended_at": "2026-06-21T10:00:00+00:00",
            "updated_at": updated_at,
        }

    @patch.dict("os.environ", {"NEWS_OBSERVER_SUMMARY_MODEL": "gpt-5.5"})
    def test_reuses_fresh_summary(self):
        cluster_id = self._insert_cluster()
        self._insert_summary(
            cluster_id,
            "Stored summary",
            "2026-06-21T11:00:00+00:00",
        )

        with patch("app.summarizer._generate_summary") as generate:
            summary = ensure_cluster_summary(self._cluster(cluster_id), [])

        self.assertEqual(summary, "Stored summary")
        generate.assert_not_called()

    @patch.dict("os.environ", {"NEWS_OBSERVER_SUMMARY_MODEL": "gpt-5.5"})
    def test_regenerates_stale_summary(self):
        cluster_id = self._insert_cluster()
        self._insert_summary(
            cluster_id,
            "Old summary",
            "2026-06-21T10:59:00+00:00",
        )

        with patch(
            "app.summarizer._generate_summary",
            return_value="Fresh summary",
        ) as generate:
            summary = ensure_cluster_summary(self._cluster(cluster_id), [])

        self.assertEqual(summary, "Fresh summary")
        generate.assert_called_once()

        with closing(sqlite3.connect(self.database_path)) as connection:
            stored = connection.execute(
                "SELECT content FROM summaries WHERE cluster_id = ?",
                (cluster_id,),
            ).fetchone()[0]

        self.assertEqual(stored, "Fresh summary")


if __name__ == "__main__":
    unittest.main()
