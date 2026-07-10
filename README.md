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
- **Target application:** Witchfire
  - Steam App ID `3156770`
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

## Future Considerations

The following were considered during design and deliberately deferred, since they don't serve the project's core analytical goal (sentiment trend across patches) or its mapping to the target job description. Noted here as conscious decisions, not oversights.

- **Per-review versioning.** Batch pulls overwrite existing reviews in place rather than preserving every prior version. The current analysis only needs accurate current state, not edit history. If a future question required tracking how reviews change over time (e.g. sentiment shift within an edited review), landing's flexible schema would allow adding a version field or switching to append-only writes without a redesign.
- **Formal backup / disaster recovery.** MongoDB Atlas does not provide managed backups on the Free (M0) tier; Atlas's own guidance for this tier is to use `mongodump`/`mongorestore` manually. Not implemented here, since the project has no production users or uptime requirement — noted as the standard approach if this were a production system.
- **Dev-time snapshotting for transform iteration.** Taking a frozen snapshot of `landing_reviews` before iterating on cleaning/transform logic avoids attributing output changes to a concurrent scheduled pull rather than a code change. Not built as tooling here; would use the same `mongodump` mechanism as backup if needed.
- **Hosted dashboard.** Metabase runs standalone by default. Hosting it is a nice-to-have, not a requirement — any BI tool (Power BI, Metabase, Tableau) can connect directly to the Postgres analysis layer regardless of whether a dashboard instance is hosted.

## Tech Stack

- **Language:** Python 3.11+
- **Storage (landing/staging):** MongoDB Atlas (Free M0 tier)
- **Storage (analysis layer):** Postgres (Neon)
- **API:** FastAPI, Fly.io
- **NLP:** spaCy (entity/keyword extraction) + Hugging Face Transformers (sentiment classification)
- **Modeling:** LightGBM, scikit-learn, served via the API's `/predict` endpoint
- **Analysis:** SQL
- **Dashboard:** Metabase
- **Orchestration:** GitHub Actions (scheduled incremental runs)

## Project Structure

```
steam-review-analysis/
├── scripts/
│   ├── test_connection.py      # MongoDB connection test (connect, insert, read, delete)
│   └── neon_connection_test.py # Postgres connection test (connect, insert, read, drop)
├── ingest/
│   ├── fetch_reviews.py        # API pagination, retry/backoff, landing writes
│   └── watermark.py            # incremental pull state tracking
├── transform/
│   └── clean_reviews.py        # dedup, typing, normalization, staging writes
├── export/
│   └── flatten_export.py       # MongoDB → Postgres flatten/export
├── analysis/
│   └── queries.sql             # trend and aggregation queries
├── nlp/
│   ├── sentiment.py            # classification
│   └── entities.py             # keyword/entity extraction
├── modeling/
│   └── train_model.py          # LightGBM training/evaluation
├── api/
│   ├── main.py                 # FastAPI app: /reviews, /sentiment/trend, /predict
│   └── deploy/                 # hosting config (Render/Railway/Fly.io)
├── dashboard/
│   └── metabase/               # Metabase config / Docker setup (standalone)
├── docs/
│   └── data_quality.md         # documented cleaning/handling decisions
├── .github/
│   └── workflows/
│       └── incremental_pull.yml    # scheduled incremental ingestion
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- A MongoDB Atlas account with an M0 cluster. Collections `landing_reviews` and `staging_reviews` must exist in your cluster.
- A Neon account with a `dev` branch. Use the dev branch connection string, not production.

### Installation

```bash
git clone <repo-url>
cd steam-review-analysis
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root (never commit this file):

```
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/dbname
NEON_DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
```

Both connection strings are loaded via `python-dotenv`. `sslmode=require` is mandatory for Neon — unencrypted connections are rejected.

### Verify connections

```bash
python scripts/test_connection.py       # MongoDB
python scripts/neon_connection_test.py  # Postgres
```

Both scripts connect, run a minimal insert/read/delete cycle, and exit cleanly on success.

### Running the pipeline

```bash
# Initial backfill
python ingest/fetch_reviews.py --mode backfill

# Subsequent incremental runs
python ingest/fetch_reviews.py --mode incremental

# Flatten and export to Postgres
python export/flatten_export.py

# Run the API locally
uvicorn api.main:app --reload

# Launch Metabase (requires Docker)
docker run -d -p 3000:3000 --name metabase metabase/metabase
```

## Roadmap

- [x] MongoDB Atlas + Neon Postgres infrastructure set up and connection-tested
- [ ] Backfill ingestion + MongoDB landing layer
- [ ] Cleaning + MongoDB staging layer
- [ ] **FastAPI skeleton deployed** (`/health` only) — validates hosting pipeline early, before real endpoints exist
- [ ] Incremental pipeline with watermark tracking
- [ ] GitHub Actions scheduled workflow
- [ ] Flatten/export to Postgres
- [ ] `/reviews` endpoint added (once Postgres is populated)
- [ ] SQL trend analysis
- [ ] `/sentiment/trend` endpoint added (once NLP output exists)
- [ ] Sentiment classification + entity extraction
- [ ] LightGBM model + evaluation
- [ ] `/predict` endpoint added (once model is trained)
- [ ] Metabase dashboard + stakeholder summary

## License

MIT