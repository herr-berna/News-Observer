from pydantic import BaseModel


class Article(BaseModel):
    id: int
    source: str
    title: str
    url: str
    published_at: str | None = None
    collected_at: str
    text: str | None = None
