from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .schemas import Article
from .services import (
    get_article,
    list_articles,
    list_articles_by_source,
    list_sources,
)


app = FastAPI(title="News Observer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/articles", response_model=list[Article])
def api_list_articles(limit: int = 50):
    return list_articles(limit=limit)


@app.get("/articles/{article_id}", response_model=Article)
def api_get_article(article_id: int):
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@app.get("/sources", response_model=list[str])
def api_list_sources():
    return list_sources()


@app.get("/sources/{source}/articles", response_model=list[Article])
def api_list_articles_by_source(source: str, limit: int = 50):
    return list_articles_by_source(source=source, limit=limit)
