from datetime import datetime, timezone

import feedparser

from .models import ArticleMetadata


def _published_at(entry) -> str | None:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return entry.get("published") or entry.get("updated")

    return datetime(*published[:6], tzinfo=timezone.utc).isoformat()


def fetch_feed(source: str, feed_url: str) -> list[ArticleMetadata]:
    parsed_feed = feedparser.parse(feed_url)
    articles = []

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
            )
        )

    return articles


def fetch_all_feeds(feeds: dict[str, str]) -> list[ArticleMetadata]:
    articles = []

    for source, feed_url in feeds.items():
        articles.extend(fetch_feed(source, feed_url))

    return articles
