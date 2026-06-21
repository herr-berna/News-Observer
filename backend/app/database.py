import sqlite3
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "news_observer.db"


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def _add_missing_columns(connection):
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(articles)").fetchall()
    }
    additions = {
        "author": "TEXT",
        "country": "TEXT",
        "language": "TEXT",
        "category": "TEXT",
        "normalized_title": "TEXT",
        "content_hash": "TEXT",
        "duplicate_of_id": "INTEGER REFERENCES articles(id)",
        "cluster_id": "INTEGER REFERENCES clusters(id)",
    }

    for name, definition in additions.items():
        if name not in columns:
            connection.execute(
                f"ALTER TABLE articles ADD COLUMN {name} {definition}"
            )


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                published_at TEXT,
                collected_at TEXT NOT NULL,
                text TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                article_count INTEGER NOT NULL DEFAULT 0,
                centroid TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _add_missing_columns(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL UNIQUE REFERENCES articles(id)
                    ON DELETE CASCADE,
                model TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                vector TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER NOT NULL REFERENCES clusters(id)
                    ON DELETE CASCADE,
                model TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS article_tags (
                article_id INTEGER NOT NULL REFERENCES articles(id)
                    ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id)
                    ON DELETE CASCADE,
                PRIMARY KEY (article_id, tag_id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_cluster_id "
            "ON articles(cluster_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_content_hash "
            "ON articles(content_hash)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_published_at "
            "ON articles(published_at)"
        )
        connection.commit()
