import logging
from datetime import datetime, timezone

from .analysis import analyze_articles
from .database import get_connection, init_db
from .extractor import extract_article_text
from .feeds import RSS_FEEDS
from .models import ArticleCreate
from .rss import fetch_all_feeds
from .summarizer import ensure_cluster_summary


logger = logging.getLogger(__name__)


def row_to_dict(row):
    return dict(row) if row else None


def list_articles(limit: int = 50):
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source, title, url, published_at, collected_at, text,
                   author, country, language, category, cluster_id,
                   duplicate_of_id
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
            SELECT id, source, title, url, published_at, collected_at, text,
                   author, country, language, category, cluster_id,
                   duplicate_of_id
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
            SELECT id, source, title, url, published_at, collected_at, text,
                   author, country, language, category, cluster_id,
                   duplicate_of_id
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
                    source, title, url, published_at, collected_at, text,
                    author, country, language, category
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.source,
                    article.title,
                    article.url,
                    article.published_at,
                    collected_at,
                    article.text,
                    article.author,
                    article.country,
                    article.language,
                    article.category,
                ),
            )
            connection.commit()
        return True
    except Exception:
        logger.exception("Could not save article: %s", article.url)
        return False


def list_clusters(limit: int = 50):
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT clusters.id, clusters.label, clusters.started_at,
                   clusters.ended_at, clusters.article_count,
                   clusters.updated_at,
                   (
                       SELECT content
                       FROM summaries
                       WHERE summaries.cluster_id = clusters.id
                       ORDER BY created_at DESC
                       LIMIT 1
                   ) AS summary,
                   (
                       SELECT GROUP_CONCAT(DISTINCT articles.source)
                       FROM articles
                       WHERE articles.cluster_id = clusters.id
                   ) AS sources,
                   (
                       SELECT GROUP_CONCAT(DISTINCT tags.name)
                       FROM articles
                       JOIN article_tags
                         ON article_tags.article_id = articles.id
                       JOIN tags ON tags.id = article_tags.tag_id
                       WHERE articles.cluster_id = clusters.id
                   ) AS keywords
            FROM clusters
            ORDER BY ended_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [_cluster_row_to_dict(row) for row in rows]


def _split_grouped_values(value):
    return value.split(",") if value else []


def _cluster_row_to_dict(row):
    cluster = row_to_dict(row)
    cluster["sources"] = _split_grouped_values(cluster.get("sources"))
    cluster["keywords"] = _split_grouped_values(cluster.get("keywords"))[:10]
    return cluster


def get_cluster(cluster_id: int):
    init_db()
    with get_connection() as connection:
        cluster = connection.execute(
            """
            SELECT clusters.id, clusters.label, clusters.started_at,
                   clusters.ended_at, clusters.article_count,
                   clusters.updated_at,
                   (
                       SELECT content
                       FROM summaries
                       WHERE summaries.cluster_id = clusters.id
                       ORDER BY created_at DESC
                       LIMIT 1
                   ) AS summary,
                   (
                       SELECT GROUP_CONCAT(DISTINCT articles.source)
                       FROM articles
                       WHERE articles.cluster_id = clusters.id
                   ) AS sources,
                   (
                       SELECT GROUP_CONCAT(DISTINCT tags.name)
                       FROM articles
                       JOIN article_tags
                         ON article_tags.article_id = articles.id
                       JOIN tags ON tags.id = article_tags.tag_id
                       WHERE articles.cluster_id = clusters.id
                   ) AS keywords
            FROM clusters
            WHERE clusters.id = ?
            """,
            (cluster_id,),
        ).fetchone()
        if not cluster:
            return None

        articles = connection.execute(
            """
            SELECT id, source, title, url, published_at, collected_at, text,
                   author, country, language, category, cluster_id,
                   duplicate_of_id
            FROM articles
            WHERE cluster_id = ?
            ORDER BY COALESCE(published_at, collected_at) DESC
            """,
            (cluster_id,),
        ).fetchall()

    result = _cluster_row_to_dict(cluster)
    result["articles"] = [row_to_dict(article) for article in articles]
    try:
        result["summary"] = ensure_cluster_summary(result, result["articles"])
    except Exception:
        logger.exception("Could not generate summary for cluster %s", cluster_id)
    return result


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

    analyze_articles(rebuild_clusters=False)
    return saved_count
