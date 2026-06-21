from datetime import datetime, timezone

import feedparser

from .feeds import SOURCE_DEFAULTS
from .models import ArticleMetadata


def _published_at(entry) -> str | None:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return entry.get("published") or entry.get("updated")

    return datetime(*published[:6], tzinfo=timezone.utc).isoformat()


def fetch_feed(source: str, feed_url: str) -> list[ArticleMetadata]:
    parsed_feed = feedparser.parse(feed_url)
    articles = []
    defaults = SOURCE_DEFAULTS.get(source, {})

    for entry in parsed_feed.entries:
        title = entry.get("title")
        link = entry.get("link")

        if not title or not link:
            continue

        articles.append(
            ArticleMetadata(
                source=source,
                title=title,
                url=link,
                published_at=_published_at(entry),
                author=entry.get("author"),
                country=defaults.get("country"),
                language=parsed_feed.feed.get("language") or defaults.get("language"),
                category=entry.get("category"),
                keywords=[
                    tag.get("term")
                    for tag in entry.get("tags", [])
                    if tag.get("term")
                ],
            )
        )

    return articles


def fetch_all_feeds(feeds: dict[str, str]) -> list[ArticleMetadata]:
    articles = []

    for source, feed_url in feeds.items():
        articles.extend(fetch_feed(source, feed_url))

    return articles
