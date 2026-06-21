import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.analysis import analyze_articles
from app.database import init_db
from app.normalizer import cosine_similarity, create_embedding, normalize_text


class NormalizerTests(unittest.TestCase):
    def test_normalizes_whitespace_and_unicode(self):
        self.assertEqual(
            normalize_text("  Prime\u00a0minister — resigns  "),
            "Prime minister - resigns",
        )

    def test_related_titles_have_higher_similarity(self):
        related = cosine_similarity(
            create_embedding("Earthquake strikes southern Japan", None),
            create_embedding("Strong earthquake hits south Japan", None),
        )
        unrelated = cosine_similarity(
            create_embedding("Earthquake strikes southern Japan", None),
            create_embedding("Football club signs new striker", None),
        )
        self.assertGreater(related, unrelated)


class AnalysisPipelineTests(unittest.TestCase):
    def setUp(self):
        self.database_path = (
            Path(__file__).parent / f".test-analysis-{uuid4().hex}.db"
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

    def _insert_article(self, source, title, text, published_at):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO articles (
                    source, title, url, published_at, collected_at, text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    title,
                    f"https://example.com/{source}/{title}",
                    published_at,
                    published_at,
                    text,
                ),
            )
            connection.commit()

    def test_groups_related_articles_and_separates_other_topics(self):
        self._insert_article(
            "Source A",
            "Powerful earthquake strikes southern Japan",
            "A powerful earthquake struck southern Japan near the coast.",
            "2026-06-21T10:00:00+00:00",
        )
        self._insert_article(
            "Source B",
            "Strong earthquake hits south Japan coast",
            "The earthquake hit Japan's southern coast on Sunday.",
            "2026-06-21T11:00:00+00:00",
        )
        self._insert_article(
            "Source C",
            "Football club signs a new striker",
            "The football club announced a new player transfer.",
            "2026-06-21T12:00:00+00:00",
        )

        result = analyze_articles()

        self.assertEqual(result["normalized_articles"], 3)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(result["clusters"], 2)

        with closing(sqlite3.connect(self.database_path)) as connection:
            cluster_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT cluster_id FROM articles ORDER BY id"
                ).fetchall()
            ]

        self.assertEqual(cluster_ids[0], cluster_ids[1])
        self.assertNotEqual(cluster_ids[0], cluster_ids[2])


if __name__ == "__main__":
    unittest.main()
