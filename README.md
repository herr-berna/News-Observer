# News Observer

News Observer is a small news aggregation project. It collects articles from RSS feeds, extracts article text, stores articles in SQLite, exposes them through a FastAPI API, and displays them in a React frontend.

## Project Structure

```text
backend/
  app/
    main.py
    database.py
    models.py
    rss.py
    extractor.py
    services.py
    feeds.py
    schemas.py
  scripts/
    collect_articles.py
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    components/
      ArticleList.jsx
      ArticleCard.jsx
  index.html
  package.json
  vite.config.js
```

## Backend Setup

From the `backend` directory:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Run the API

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

Available endpoints:

- `GET /articles`
- `GET /articles/{id}`
- `GET /sources`
- `GET /sources/{source}/articles`

## Collect Articles

From the `backend` directory:

```bash
python scripts/collect_articles.py
```

This reads the configured RSS feeds, extracts article text, and saves new articles to SQLite. Duplicate articles are skipped using the article URL.

After collection, articles are normalized, embedded, checked for near-duplicates,
and assigned to event clusters automatically.

To rebuild the analysis for all stored articles:

```bash
python scripts/analyze_articles.py
```

The first MVP uses deterministic local hashing embeddings, cosine similarity,
and a 72-hour event window. To favor precision for outlet comparison, each
event accepts at most one non-duplicate article from the same source. The
pipeline does not require an external AI API.

Additional endpoints:

- `GET /clusters`
- `GET /clusters/{id}`

## Frontend Setup

From the `frontend` directory:

```bash
npm install
npm run dev
```

if you have trouble with powershell:

```bash
npm.cmd run dev
```

The React app runs at `http://localhost:5173` and expects the backend API at `http://localhost:8000`.

To point the frontend at a different API URL, set `VITE_API_BASE_URL`.
