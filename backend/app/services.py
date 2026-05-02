from datetime import datetime, timezone

from .database import get_connection, init_db
from .extractor import extract_article_text
from .feeds import RSS_FEEDS
from .models import ArticleCreate
from .rss import fetch_all_feeds


def row_to_dict(row):
    return dict(row) if row else None


def list_articles(limit: int = 50):
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source, title, url, published_at, collected_at, text
            FROM articles
            ORDER BY COALESCE(published_at, collected_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [row_to_dict(row) for row in rows]


def get_article(article_id: int):
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, source, title, url, published_at, collected_at, text
            FROM articles
            WHERE id = ?
            """,
            (article_id,),
        ).fetchone()

    return row_to_dict(row)


def list_sources():
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT source
            FROM articles
            ORDER BY source
            """
        ).fetchall()

    stored_sources = [row["source"] for row in rows]
    configured_sources = list(RSS_FEEDS.keys())
    return sorted(set(configured_sources + stored_sources))


def list_articles_by_source(source: str, limit: int = 50):
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source, title, url, published_at, collected_at, text
            FROM articles
            WHERE lower(source) = lower(?)
            ORDER BY COALESCE(published_at, collected_at) DESC
            LIMIT ?
            """,
            (source, limit),
        ).fetchall()

    return [row_to_dict(row) for row in rows]


def article_exists(url: str) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM articles WHERE url = ?",
            (url,),
        ).fetchone()

    return row is not None


def save_article(article: ArticleCreate) -> bool:
    collected_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO articles (
                    source, title, url, published_at, collected_at, text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    article.source,
                    article.title,
                    article.url,
                    article.published_at,
                    collected_at,
                    article.text,
                ),
            )
            connection.commit()
        return True
    except Exception:
        return False


def collect_articles() -> int:
    init_db()
    saved_count = 0

    for metadata in fetch_all_feeds(RSS_FEEDS):
        if article_exists(metadata.url):
            continue

        try:
            text = extract_article_text(metadata.url)
        except Exception:
            text = None

        article = ArticleCreate(
            source=metadata.source,
            title=metadata.title,
            url=metadata.url,
            published_at=metadata.published_at,
            text=text,
        )

        if save_article(article):
            saved_count += 1

    return saved_count
