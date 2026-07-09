# Steam Review Analysis

An end-to-end data pipeline that ingests, processes, and analyzes Steam user reviews for Steam games, turning raw review data into structured insights on player sentiment, recurring feedback themes, and how sentiment shifts across game updates. The scope of the current stage is focused on the game *Witchfire*.

## Overview

Early Access games evolve rapidly through frequent patches, and player sentiment shifts alongside them. This project builds a pipeline to track that shift over time — ingesting reviews directly from Steam's public API, cleaning and structuring the data, extracting sentiment and thematic signal via NLP, and surfacing the results through queries and a dashboard.

The pipeline is designed to run incrementally: rather than re-pulling the full review history on each run, it tracks a watermark and ingests only new or updated reviews, so it can be scheduled to run on an ongoing basis as new reviews are posted.

## Architecture

```
Steam Reviews API
       │
       ▼
 [Ingestion] ── MongoDB: landing_reviews (raw, unmodified)
       │
       ▼
 [Transform] ── MongoDB: staging_reviews (deduped, typed, cleaned)
       │
       ▼
 [Flatten/Export] ── Postgres: analysis tables (SQL-ready, connectable by any BI tool)
       │
       ├──▶ [SQL Analysis] ── joins, aggregations, window functions
       │
       ├──▶ [NLP] ── sentiment classification, entity/keyword extraction
       │
       └──▶ [Modeling] ── LightGBM classifier on review outcome
                  │
                  ▼
       [FastAPI] (hosted) ── /reviews  /sentiment/trend  /predict
                  │
                  ▼
       [Dashboard] ── Metabase, standalone (hosting optional)
```

## Data Source

- **API:** [Steam Store Reviews API](https://partner.steamgames.com/doc/store/getreviews) (`store.steampowered.com/appreviews/{appid}`)
- **Target application:** Witchfire — Steam App ID `3156770`
- **Scope:** English-language reviews, backfilled to cover the full patch history to date, with incremental updates thereafter

## Pipeline Stages

### 1. Ingestion
Pulls reviews via cursor-based pagination, with retry/backoff handling for rate limits. Raw API responses are landed unmodified into MongoDB's `landing_reviews` collection, preserving all fields (including nested author/playtime metadata) for downstream flexibility. A logged watermark tracks the last successful pull, enabling incremental runs.

### 2. Transformation
Raw documents are deduplicated, typed, and normalized into MongoDB's `staging_reviews` collection. Data quality issues (nulls, malformed dates, outlier playtime values) are identified and handled explicitly, with each decision documented in `docs/data_quality.md`.

### 3. Flatten & Export
Cleaned documents in `staging_reviews` are flattened (nested fields such as `author.playtime_forever` mapped to flat columns) and exported into Postgres, giving the project a standard relational layer that any SQL client or BI tool (Power BI, Metabase, Tableau, etc.) can connect to directly.

### 4. Analysis
SQL queries against the Postgres tables surface trends: rolling sentiment averages, review volume by month, and sentiment shifts before/after each known patch date, using joins, aggregations, and window functions.

### 5. NLP
Review text is classified for sentiment and mined for recurring entities and keywords (weapons, mechanics, performance issues, content complaints), using a time-aware train/test split to avoid leakage across the evolving review corpus.

### 6. Modeling
A LightGBM classifier predicts review outcome from metadata and text-derived features, evaluated on precision/recall given class imbalance in the review distribution.

### 7. API
A FastAPI service, deployed to a hosted environment, exposes the pipeline's outputs as endpoints (`/reviews`, `/sentiment/trend`, `/predict`) — turning the pipeline from a local script into a consumable backend service.

### 8. Reporting
Findings are surfaced through a Metabase dashboard (volume trend, sentiment trend across patches, flagged high-signal reviews) and a plain-language summary for non-technical stakeholders. The dashboard runs standalone by default; hosting it is an optional extension, not a requirement — analysts using other BI tools (Power BI, etc.) can connect directly to the Postgres analysis layer instead.

## Tech Stack

- **Language:** Python 3.11+
- **Storage (landing/staging):** MongoDB Atlas
- **Storage (analysis layer):** Postgres (Supabase/Neon), populated via flatten/export from MongoDB — a standard connection target for any BI tool
- **API:** FastAPI, hosted (Render/Railway/Fly.io)
- **NLP:** spaCy (entity/keyword extraction) + Hugging Face Transformers (sentiment classification)
- **Modeling:** LightGBM, scikit-learn, served via the API's `/predict` endpoint
- **Analysis:** SQL (joins, aggregations, window functions)
- **Dashboard:** Metabase (standalone; hosting optional)
- **Orchestration:** GitHub Actions (scheduled incremental runs)

## Project Structure

```
steam-review-analysis/
├── ingest/
│   ├── fetch_reviews.py       # API pagination, retry/backoff, landing writes
│   └── watermark.py           # incremental pull state tracking
├── transform/
│   └── clean_reviews.py       # dedup, typing, normalization, staging writes
├── export/
│   └── flatten_export.py      # MongoDB → Postgres flatten/export
├── analysis/
│   └── queries.sql            # trend and aggregation queries
├── nlp/
│   ├── sentiment.py           # classification
│   └── entities.py            # keyword/entity extraction
├── modeling/
│   └── train_model.py         # LightGBM training/evaluation
├── api/
│   ├── main.py                 # FastAPI app: /reviews, /sentiment/trend, /predict
│   └── deploy/                 # hosting config (Render/Railway/Fly.io)
├── dashboard/
│   └── metabase/               # Metabase config / Docker setup (standalone)
├── docs/
│   └── data_quality.md        # documented cleaning/handling decisions
├── .github/
│   └── workflows/
│       └── incremental_pull.yml   # scheduled incremental ingestion
└── README.md
```

## Setup

```bash
git clone <repo-url>
cd steam-review-analysis
pip install -r requirements.txt

# Set connection strings
export MONGODB_URI="<connection-string>"
export POSTGRES_URI="<connection-string>"

# Run initial backfill
python ingest/fetch_reviews.py --mode backfill

# Run incremental update (subsequent runs)
python ingest/fetch_reviews.py --mode incremental

# Flatten and export to Postgres for analysis
python export/flatten_export.py

# Run the API locally
uvicorn api.main:app --reload
# (deployed separately to Render/Railway/Fly.io for hosted access)

# Launch Metabase (requires Docker) — standalone, connects to Postgres
docker run -d -p 3000:3000 --name metabase metabase/metabase
```

## Roadmap

- [ ] Backfill ingestion + MongoDB landing layer
- [ ] Cleaning + MongoDB staging layer
- [ ] Incremental pipeline with watermark tracking
- [ ] GitHub Actions scheduled workflow
- [ ] Flatten/export to Postgres
- [ ] SQL trend analysis
- [ ] Sentiment classification + entity extraction
- [ ] LightGBM model + evaluation
- [ ] FastAPI service (`/reviews`, `/sentiment/trend`, `/predict`) + hosting
- [ ] Metabase dashboard + stakeholder summary

## License

MIT