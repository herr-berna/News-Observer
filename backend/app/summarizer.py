import os
from datetime import datetime, timezone

from . import config  # noqa: F401
from .database import get_connection, init_db


SUMMARY_MODEL = os.getenv("NEWS_OBSERVER_SUMMARY_MODEL", "gpt-5.5")
SUMMARY_INSTRUCTIONS = """
You are NewsObserver's neutral news summarizer.

Write a concise, neutral summary of the event represented by the articles.
Rules:
- Use only the information provided in the articles.
- Do not favor one outlet.
- Avoid loaded language and speculation.
- If outlets disagree or emphasize different facts, mention that carefully.
- Do not invent entities, causes, motives, numbers, or outcomes.
- Write 2 short paragraphs followed by 3 bullet points titled "Key points".
- Do not include markdown links.
""".strip()


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _summary_is_fresh(summary_updated_at: str | None, cluster_updated_at: str) -> bool:
    if not summary_updated_at:
        return False
    return _parse_date(summary_updated_at) >= _parse_date(cluster_updated_at)


def _article_excerpt(text: str | None, limit: int = 900) -> str:
    if not text:
        return "No article body was extracted."
    cleaned = " ".join(text.split())
    return cleaned[:limit]


def _build_summary_input(cluster: dict, articles: list[dict]) -> str:
    article_blocks = []
    for index, article in enumerate(articles, start=1):
        published_at = article.get("published_at") or article.get("collected_at")
        article_blocks.append(
            "\n".join(
                [
                    f"Article {index}",
                    f"Source: {article.get('source')}",
                    f"Title: {article.get('title')}",
                    f"Published: {published_at}",
                    f"Author: {article.get('author') or 'Unknown'}",
                    f"Category: {article.get('category') or 'Unknown'}",
                    f"Excerpt: {_article_excerpt(article.get('text'))}",
                ]
            )
        )

    return "\n\n".join(
        [
            f"Event label: {cluster['label']}",
            f"Event window: {cluster.get('started_at')} to {cluster.get('ended_at')}",
            "Articles:",
            "\n\n---\n\n".join(article_blocks),
        ]
    )


def _generate_summary(cluster: dict, articles: list[dict]) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "AI summaries require the `openai` package. "
            "Install backend requirements with `pip install -r requirements.txt`."
        ) from exc

    response = OpenAI().responses.create(
        model=os.getenv("NEWS_OBSERVER_SUMMARY_MODEL", SUMMARY_MODEL),
        instructions=SUMMARY_INSTRUCTIONS,
        input=_build_summary_input(cluster, articles),
    )
    return response.output_text.strip()


def get_stored_summary(connection, cluster_id: int):
    return connection.execute(
        """
        SELECT id, model, content, created_at, updated_at
        FROM summaries
        WHERE cluster_id = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (cluster_id,),
    ).fetchone()


def ensure_cluster_summary(cluster: dict, articles: list[dict]) -> str | None:
    init_db()
    summary_model = os.getenv("NEWS_OBSERVER_SUMMARY_MODEL", SUMMARY_MODEL)

    with get_connection() as connection:
        stored_summary = get_stored_summary(connection, cluster["id"])
        if stored_summary and stored_summary["model"] == summary_model:
            if _summary_is_fresh(
                stored_summary["updated_at"],
                cluster["updated_at"],
            ):
                return stored_summary["content"]

    summary = _generate_summary(cluster, articles)
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        stored_summary = get_stored_summary(connection, cluster["id"])
        if stored_summary:
            connection.execute(
                """
                UPDATE summaries
                SET model = ?, content = ?, updated_at = ?
                WHERE id = ?
                """,
                (summary_model, summary, now, stored_summary["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO summaries (
                    cluster_id, model, content, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (cluster["id"], summary_model, summary, now, now),
            )
        connection.commit()

    return summary
