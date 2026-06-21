from pydantic import BaseModel, Field


class Article(BaseModel):
    id: int
    source: str
    title: str
    url: str
    published_at: str | None = None
    collected_at: str
    text: str | None = None
    author: str | None = None
    country: str | None = None
    language: str | None = None
    category: str | None = None
    cluster_id: int | None = None
    duplicate_of_id: int | None = None


class Cluster(BaseModel):
    id: int
    label: str
    started_at: str | None = None
    ended_at: str | None = None
    article_count: int
    summary: str | None = None
    sources: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ClusterDetail(Cluster):
    articles: list[Article]
