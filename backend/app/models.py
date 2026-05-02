from dataclasses import dataclass


@dataclass
class ArticleMetadata:
    source: str
    title: str
    url: str
    published_at: str | None = None


@dataclass
class ArticleCreate(ArticleMetadata):
    text: str | None = None
