from dataclasses import dataclass


@dataclass
class ArticleMetadata:
    source: str
    title: str
    url: str
    published_at: str | None = None
    author: str | None = None
    country: str | None = None
    language: str | None = None
    category: str | None = None
    keywords: list[str] | None = None


@dataclass
class ArticleCreate(ArticleMetadata):
    text: str | None = None
