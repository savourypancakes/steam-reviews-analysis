# Steam Review Analysis 

An end-to-end data pipeline that ingests, processes, and analyzes Steam user reviews for steam games, turning raw review data into structured insights on player sentiment, recurring feedback themes, and how sentiment shifts across game updates. The scope of the current stage is focused on the game *Witchfire*.

## Overview

Early Access games evolve rapidly through frequent patches, and player sentiment shifts alongside them. This project builds a pipeline to track that shift over time — ingesting reviews directly from Steam's public API, cleaning and structuring the data, extracting sentiment and thematic signal via NLP, and surfacing the results through queries and a dashboard.

The pipeline is designed to run incrementally: rather than re-pulling the full review history on each run, it tracks a watermark and ingests only new or updated reviews, so it can be scheduled to run on an ongoing basis as new reviews are posted.

## Architecture

```
Steam Reviews API
       │
       ▼
 [Ingestion] ── landing_reviews (raw, unmodified)
       │
       ▼
 [Transform] ── staging_reviews (deduped, typed, cleaned)
       │
       ├──▶ [SQL Analysis] ── trend & aggregation queries
       │
       ├──▶ [NLP] ── sentiment classification, entity/keyword extraction
       │
       └──▶ [Modeling] ── gradient-boosted classifier on review outcome
                  │
                  ▼
            [Dashboard] ── volume, sentiment trend, flagged reviews
```

## Data Source

- **API:** [Steam Store Reviews API](https://partner.steamgames.com/doc/store/getreviews) (`store.steampowered.com/appreviews/{appid}`)
- **Target application:** Witchfire — Steam App ID `3156770`
- **Scope:** English-language reviews, backfilled to cover the full patch history to date, with incremental updates thereafter

## Pipeline Stages

### 1. Ingestion
Pulls reviews via cursor-based pagination, with retry/backoff handling for rate limits. Raw API responses are landed unmodified into `landing_reviews`, preserving all fields (including nested author/playtime metadata) for downstream flexibility. A logged watermark tracks the last successful pull, enabling incremental runs.

### 2. Transformation
Raw data is deduplicated, typed, and normalized into `staging_reviews`. Data quality issues (nulls, malformed dates, outlier playtime values) are identified and handled explicitly, with each decision documented in `docs/data_quality.md`.

### 3. Analysis
SQL queries against the staging layer surface trends: rolling sentiment averages, review volume by month, and sentiment shifts before/after each known patch date.

### 4. NLP
Review text is classified for sentiment and mined for recurring entities and keywords (weapons, mechanics, performance issues, content complaints), using a time-aware train/test split to avoid leakage across the evolving review corpus.

### 5. Modeling
A gradient-boosted model (XGBoost/LightGBM) predicts review outcome from metadata and text-derived features, evaluated on precision/recall given class imbalance in the review distribution.

### 6. Reporting
Findings are surfaced through a dashboard (volume trend, sentiment trend across patches, flagged high-signal reviews) and a plain-language summary for non-technical stakeholders.

## Tech Stack

- **Language:** Python
- **Storage:** SQLite (landing/staging layers)
- **NLP:** spaCy / Hugging Face Transformers
- **Modeling:** XGBoost / LightGBM, scikit-learn
- **Analysis:** SQL (window functions, aggregations)
- **Dashboard:** Streamlit / Metabase
- **Scheduling:** cron / GitHub Actions (for incremental runs)

## Project Structure

```
witchfire-pipeline/
├── ingest/
│   ├── fetch_reviews.py       # API pagination, retry/backoff, landing writes
│   └── watermark.py           # incremental pull state tracking
├── transform/
│   └── clean_reviews.py       # dedup, typing, normalization, staging writes
├── analysis/
│   └── queries.sql            # trend and aggregation queries
├── nlp/
│   ├── sentiment.py           # classification
│   └── entities.py            # keyword/entity extraction
├── modeling/
│   └── train_model.py         # gradient-boosted model training/evaluation
├── dashboard/
│   └── app.py                 # Streamlit dashboard
├── docs/
│   └── data_quality.md        # documented cleaning/handling decisions
└── README.md
```

## Setup

```bash
git clone <repo-url>
cd witchfire-pipeline
pip install -r requirements.txt

# Run initial backfill
python ingest/fetch_reviews.py --mode backfill

# Run incremental update (subsequent runs)
python ingest/fetch_reviews.py --mode incremental
```

## Roadmap

- [ ] Backfill ingestion + landing layer
- [ ] Cleaning + staging layer
- [ ] Incremental pipeline with watermark tracking
- [ ] SQL trend analysis
- [ ] Sentiment classification + entity extraction
- [ ] Predictive model + evaluation
- [ ] Dashboard + stakeholder summary

## License

MIT