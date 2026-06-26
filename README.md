# News Observer

News Observer is an intelligent news aggregation project. It collects articles from RSS feeds, extracts article text, stores articles in SQLite, groups articles about the same event into clusters, exposes the data through a FastAPI API, and displays the grouped coverage in a React dashboard.

The current MVP follows this flow:

```text
RSS feeds
  ↓
Fetcher / text extractor
  ↓
SQLite database
  ↓
Normalization + keyword extraction
  ↓
Duplicate detection
  ↓
Event clustering
  ↓
Dashboard
```

The goal is to make articles less important as isolated items and make events the main unit of analysis. An event cluster can contain articles from different outlets that appear to be covering the same story.

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
    normalizer.py
    analysis.py
  scripts/
    collect_articles.py
    analyze_articles.py
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    components/
      EventList.jsx
      EventCard.jsx
      EventDetail.jsx
      CoverageCard.jsx
  index.html
  package.json
  vite.config.js
```

## Data Model

The main stored entities are:

- `articles`: raw and normalized article records.
- `embeddings`: local vector representation for each article.
- `clusters`: event groups built from related non-duplicate articles.
- `summaries`: reserved for future AI-generated event summaries.
- `tags` and `article_tags`: extracted keywords connected to articles.

Articles contain these analysis-oriented fields:

- `title`
- `published_at`
- `source`
- `author`
- `country`
- `language`
- `category`
- `normalized_title`
- `content_hash`
- `duplicate_of_id`
- `cluster_id`

Keywords are stored through the `tags` / `article_tags` tables, while embeddings are stored separately in the `embeddings` table.

## How Clustering and Analysis Works

The analysis pipeline lives mainly in `backend/app/analysis.py` and `backend/app/normalizer.py`.

It runs in three stages:

```text
normalize_and_embed_articles()
  ↓
detect_duplicates()
  ↓
cluster_articles()
```

### 1. Normalization and keyword extraction

Each article title and text is normalized before analysis:

- Unicode text is normalized.
- Curly quotes and long dashes are converted into simpler characters.
- Extra whitespace is collapsed.
- Text is case-folded for comparison.
- Common stop words such as `the`, `and`, `of`, `to`, and `said` are ignored during tokenization.

The system also extracts up to 10 keywords per article. Words from the title receive extra weight because RSS article bodies can be noisy, short, or repetitive.

### 2. Semantic embeddings

The current MVP supports semantic OpenAI embeddings and keeps the deterministic local hashing model as an offline fallback.

By default, the embedding provider is `auto`:

- if `OPENAI_API_KEY` is available, News Observer uses OpenAI embeddings;
- if no API key is available, it falls back to the local hashing model.

The default semantic model is:

```text
text-embedding-3-small
```

Internally, stored OpenAI embedding rows are marked with the model name:

```text
openai:text-embedding-3-small
```

OpenAI embeddings convert article text into vectors where distance represents semantic relatedness. This is useful for clustering because two articles can be grouped even when they use different wording for the same event.

The fallback local model builds a 384-dimensional vector from:

- title tokens, with high weight;
- body tokens, with lower weight;
- title bigrams, meaning pairs of neighboring title words.

Each token is hashed into a vector position, assigned a positive or negative sign, and added to the vector. The final vector is normalized so cosine similarity can be used.

The fallback approach is not as semantically powerful as an AI embedding model, but it has useful MVP properties:

- it is fast;
- it is free;
- it is deterministic;
- it works offline;
- it is good enough to catch many near-identical or strongly related headlines.

The fallback embedding model is identified as `hashing-v2`.

To force OpenAI embeddings, create a `backend/.env` file:

```env
OPENAI_API_KEY=your_api_key_here
NEWS_OBSERVER_EMBEDDING_PROVIDER=openai
```

You can copy the example file first:

```bash
copy backend\.env.example backend\.env
```

On macOS or Linux:

```bash
cp backend/.env.example backend/.env
```

You can also override the model inside `backend/.env`:

```env
NEWS_OBSERVER_EMBEDDING_MODEL=text-embedding-3-small
NEWS_OBSERVER_SUMMARY_MODEL=gpt-5.5
```

After changing embedding providers or models, rebuild the analysis:

```bash
python scripts/analyze_articles.py
```

### 3. Duplicate detection

Duplicate detection runs before clustering.

An article can be marked as a duplicate in two ways:

- exact content match using `content_hash`;
- near-duplicate match using cosine similarity.

The current near-duplicate threshold is:

```text
DUPLICATE_SIMILARITY_THRESHOLD = 0.92
```

Only articles within a recent comparison window are checked against each other, so old stories do not accidentally absorb newer unrelated stories. Duplicate articles receive `duplicate_of_id`, pointing to the first accepted article.

Duplicates are not used as independent cluster seeds. After clusters are created, duplicates inherit the `cluster_id` of their original article.

### 4. Event clustering

Clustering tries to answer: “Are these articles from different sources covering the same real-world event?”

Only non-duplicate articles that do not already have a `cluster_id` are considered. Articles are processed chronologically.

For each article, the algorithm searches for candidate clusters that:

- are within a 72-hour event window;
- do not already contain a non-duplicate article from the same source.

The same-source rule is intentional. It makes the clustering conservative and favors the product goal of comparing coverage across outlets. If BBC publishes three similar articles about the same story, the MVP avoids letting those three articles dominate one event cluster.

The current event window is:

```text
CLUSTER_WINDOW_HOURS = 72
```

A candidate cluster is scored using a combined similarity:

```text
combined_score = 0.75 * cosine_similarity + 0.25 * title_overlap
```

Title overlap is calculated after removing generic event words such as `live`, `latest`, `news`, `video`, `world`, `war`, and `cup`.

Semantic similarity is allowed to help group articles with different wording, but the algorithm still avoids broad topic-only matches. If two titles have no meaningful token overlap, their cosine similarity must be especially strong before they can be grouped.

The current cluster threshold depends on the embedding provider:

```text
HASHING_CLUSTER_SIMILARITY_THRESHOLD = 0.22
SEMANTIC_CLUSTER_SIMILARITY_THRESHOLD = 0.42
```

If the best candidate score is above the threshold, the article joins that cluster. Otherwise, a new cluster is created.

Each cluster stores:

- a `label`, currently the first article title in the cluster;
- `started_at` and `ended_at`;
- `article_count`;
- a centroid vector, updated as articles join;
- timestamps for creation and update.

### 5. Dashboard usage

The frontend dashboard uses the cluster endpoints, not just the raw article list.

Available analysis endpoints:

- `GET /clusters`
- `GET /clusters/{id}`

The dashboard shows event cards, keywords, sources, summaries, and the articles grouped under the selected event. This makes it possible to compare how different outlets covered the same story.

## Neutral AI Summaries

News Observer generates neutral summaries lazily, when an event detail page is opened through:

- `GET /clusters/{id}`

The cluster list endpoint does not generate summaries. This avoids spending API calls while the user is only browsing the dashboard.

Summaries are stored in the `summaries` table with:

- `cluster_id`
- `model`
- `content`
- `created_at`
- `updated_at`

The API reuses a stored summary when it is still fresh. A summary is considered fresh when its `updated_at` timestamp is newer than or equal to the cluster's `updated_at` timestamp.

That means:

- first time opening a story: generate and store a summary;
- opening the same story again: reuse the stored summary;
- after RSS collection adds a new article to that cluster: the cluster `updated_at` changes;
- next time that story is opened: regenerate the summary and update the stored row.

The default summary model is configured in `backend/.env`:

```env
NEWS_OBSERVER_SUMMARY_MODEL=gpt-5.5
```

The summary prompt asks for a neutral synthesis using only the articles in the cluster. It should avoid speculation, avoid favoring one outlet, and mention outlet differences carefully when relevant.

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
- `GET /clusters`
- `GET /clusters/{id}`

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

The MVP uses semantic OpenAI embeddings when `OPENAI_API_KEY` is configured.
Without an API key, it falls back to deterministic local hashing embeddings.
To favor precision for outlet comparison, each event accepts at most one
non-duplicate article from the same source.

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
