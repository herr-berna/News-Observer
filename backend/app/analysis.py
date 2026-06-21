import json
from datetime import datetime, timedelta, timezone

from .database import get_connection, init_db
from .normalizer import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    content_fingerprint,
    cosine_similarity,
    create_embedding,
    extract_keywords,
    normalize_text,
    tokenize,
)


CLUSTER_WINDOW_HOURS = 72
CLUSTER_SIMILARITY_THRESHOLD = 0.22
DUPLICATE_SIMILARITY_THRESHOLD = 0.92
EVENT_STOP_WORDS = {
    "day",
    "latest",
    "live",
    "match",
    "matches",
    "news",
    "play",
    "plays",
    "show",
    "shows",
    "team",
    "test",
    "video",
    "war",
    "watch",
    "week",
    "world",
    "cup",
}


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _event_date(article) -> datetime:
    return _parse_date(article["published_at"] or article["collected_at"])


def _store_tags(connection, article_id: int, keywords: list[str]):
    connection.execute(
        "DELETE FROM article_tags WHERE article_id = ?",
        (article_id,),
    )
    for keyword in keywords:
        connection.execute(
            "INSERT OR IGNORE INTO tags(name) VALUES (?)",
            (keyword,),
        )
        tag = connection.execute(
            "SELECT id FROM tags WHERE name = ?",
            (keyword,),
        ).fetchone()
        connection.execute(
            "INSERT OR IGNORE INTO article_tags(article_id, tag_id) VALUES (?, ?)",
            (article_id, tag["id"]),
        )


def normalize_and_embed_articles() -> int:
    init_db()
    processed = 0

    with get_connection() as connection:
        articles = connection.execute(
            """
            SELECT id, title, text
            FROM articles
            WHERE normalized_title IS NULL
               OR content_hash IS NULL
               OR NOT EXISTS (
                    SELECT 1 FROM embeddings
                    WHERE embeddings.article_id = articles.id
                      AND embeddings.model = ?
               )
            """,
            (EMBEDDING_MODEL,),
        ).fetchall()

        for article in articles:
            normalized_title = normalize_text(article["title"])
            fingerprint = content_fingerprint(article["title"], article["text"])
            keywords = extract_keywords(article["title"], article["text"])
            embedding = create_embedding(article["title"], article["text"])
            now = datetime.now(timezone.utc).isoformat()

            connection.execute(
                """
                UPDATE articles
                SET normalized_title = ?, content_hash = ?
                WHERE id = ?
                """,
                (normalized_title, fingerprint, article["id"]),
            )
            connection.execute(
                """
                INSERT INTO embeddings (
                    article_id, model, dimensions, vector, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    model = excluded.model,
                    dimensions = excluded.dimensions,
                    vector = excluded.vector,
                    created_at = excluded.created_at
                """,
                (
                    article["id"],
                    EMBEDDING_MODEL,
                    EMBEDDING_DIMENSIONS,
                    json.dumps(embedding),
                    now,
                ),
            )
            _store_tags(connection, article["id"], keywords)
            processed += 1

        connection.commit()

    return processed


def detect_duplicates() -> int:
    init_db()
    duplicates = 0

    with get_connection() as connection:
        articles = connection.execute(
            """
            SELECT articles.id, articles.content_hash, articles.published_at,
                   articles.collected_at, embeddings.vector
            FROM articles
            JOIN embeddings ON embeddings.article_id = articles.id
            ORDER BY COALESCE(articles.published_at, articles.collected_at),
                     articles.id
            """
        ).fetchall()

        accepted = []
        hashes = {}
        for article in articles:
            duplicate_of = hashes.get(article["content_hash"])
            article_date = _event_date(article)
            vector = json.loads(article["vector"])

            if duplicate_of is None:
                for previous in reversed(accepted):
                    if article_date - previous["date"] > timedelta(days=7):
                        break
                    if cosine_similarity(vector, previous["vector"]) >= (
                        DUPLICATE_SIMILARITY_THRESHOLD
                    ):
                        duplicate_of = previous["id"]
                        break

            connection.execute(
                "UPDATE articles SET duplicate_of_id = ? WHERE id = ?",
                (duplicate_of, article["id"]),
            )

            if duplicate_of is None:
                hashes[article["content_hash"]] = article["id"]
                accepted.append(
                    {"id": article["id"], "date": article_date, "vector": vector}
                )
            else:
                duplicates += 1

        connection.commit()

    return duplicates


def _event_tokens(title: str) -> list[str]:
    return [token for token in tokenize(title) if token not in EVENT_STOP_WORDS]


def _event_text(title: str) -> str:
    return " ".join(_event_tokens(title))


def _title_overlap(left: str, right: str) -> float:
    left_tokens = set(_event_tokens(left))
    right_tokens = set(_event_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _combined_similarity(article, cluster) -> float:
    overlap = _title_overlap(article["title"], cluster["label"])
    if overlap == 0:
        return 0.0

    cosine = cosine_similarity(article["vector"], cluster["centroid"])
    return 0.75 * cosine + 0.25 * overlap


def _updated_centroid(
    centroid: list[float],
    vector: list[float],
    count: int,
) -> list[float]:
    return [
        ((value * count) + new_value) / (count + 1)
        for value, new_value in zip(centroid, vector)
    ]


def cluster_articles(rebuild: bool = True) -> int:
    init_db()
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        if rebuild:
            connection.execute("UPDATE articles SET cluster_id = NULL")
            connection.execute("DELETE FROM summaries")
            connection.execute("DELETE FROM clusters")

        rows = connection.execute(
            """
            SELECT articles.id, articles.title, articles.published_at,
                   articles.collected_at, articles.source, embeddings.vector
            FROM articles
            JOIN embeddings ON embeddings.article_id = articles.id
            WHERE articles.duplicate_of_id IS NULL
              AND articles.cluster_id IS NULL
            ORDER BY COALESCE(articles.published_at, articles.collected_at),
                     articles.id
            """
        ).fetchall()

        clusters = []
        if not rebuild:
            stored_clusters = connection.execute(
                "SELECT * FROM clusters ORDER BY ended_at, id"
            ).fetchall()
            clusters = [
                {
                    "id": cluster["id"],
                    "label": cluster["label"],
                    "started_at": _parse_date(cluster["started_at"]),
                    "ended_at": _parse_date(cluster["ended_at"]),
                    "count": cluster["article_count"],
                    "centroid": json.loads(cluster["centroid"]),
                    "sources": {
                        row["source"]
                        for row in connection.execute(
                            "SELECT DISTINCT source FROM articles "
                            "WHERE cluster_id = ?",
                            (cluster["id"],),
                        ).fetchall()
                    },
                }
                for cluster in stored_clusters
            ]

        for row in rows:
            article = {
                "id": row["id"],
                "title": row["title"],
                "source": row["source"],
                "date": _event_date(row),
                "vector": create_embedding(_event_text(row["title"]), None),
            }
            candidates = [
                cluster
                for cluster in clusters
                if abs(article["date"] - cluster["ended_at"])
                <= timedelta(hours=CLUSTER_WINDOW_HOURS)
                and article["source"] not in cluster["sources"]
            ]
            best_cluster = None
            best_score = CLUSTER_SIMILARITY_THRESHOLD

            for candidate in candidates:
                score = _combined_similarity(article, candidate)
                if score > best_score:
                    best_score = score
                    best_cluster = candidate

            if best_cluster is None:
                cursor = connection.execute(
                    """
                    INSERT INTO clusters (
                        label, started_at, ended_at, article_count,
                        centroid, created_at, updated_at
                    )
                    VALUES (?, ?, ?, 1, ?, ?, ?)
                    """,
                    (
                        article["title"],
                        article["date"].isoformat(),
                        article["date"].isoformat(),
                        json.dumps(article["vector"]),
                        now,
                        now,
                    ),
                )
                best_cluster = {
                    "id": cursor.lastrowid,
                    "label": article["title"],
                    "started_at": article["date"],
                    "ended_at": article["date"],
                    "count": 1,
                    "centroid": article["vector"],
                    "sources": {article["source"]},
                }
                clusters.append(best_cluster)
            else:
                old_count = best_cluster["count"]
                best_cluster["centroid"] = _updated_centroid(
                    best_cluster["centroid"],
                    article["vector"],
                    old_count,
                )
                best_cluster["count"] += 1
                best_cluster["sources"].add(article["source"])
                best_cluster["started_at"] = min(
                    best_cluster["started_at"], article["date"]
                )
                best_cluster["ended_at"] = max(
                    best_cluster["ended_at"], article["date"]
                )
                connection.execute(
                    """
                    UPDATE clusters
                    SET started_at = ?, ended_at = ?, article_count = ?,
                        centroid = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        best_cluster["started_at"].isoformat(),
                        best_cluster["ended_at"].isoformat(),
                        best_cluster["count"],
                        json.dumps(best_cluster["centroid"]),
                        now,
                        best_cluster["id"],
                    ),
                )

            connection.execute(
                "UPDATE articles SET cluster_id = ? WHERE id = ?",
                (best_cluster["id"], article["id"]),
            )

        connection.execute(
            """
            UPDATE articles
            SET cluster_id = (
                SELECT original.cluster_id
                FROM articles AS original
                WHERE original.id = articles.duplicate_of_id
            )
            WHERE duplicate_of_id IS NOT NULL
            """
        )
        connection.commit()

    return len(clusters)


def analyze_articles(rebuild_clusters: bool = True) -> dict[str, int]:
    normalized = normalize_and_embed_articles()
    duplicates = detect_duplicates()
    clusters = cluster_articles(rebuild=rebuild_clusters)
    return {
        "normalized_articles": normalized,
        "duplicates": duplicates,
        "clusters": clusters,
    }
