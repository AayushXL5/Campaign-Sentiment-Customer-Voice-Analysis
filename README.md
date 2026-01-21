# Campaign Sentiment & Customer Voice Analysis

> An automated sentiment tracking pipeline that captures the **voice of the customer** and guides **campaign optimization** decisions.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture & Pipeline](#architecture--pipeline)
- [Data Store](#data-store)
- [How to Run](#how-to-run)
- [Pipeline Deep Dive](#pipeline-deep-dive)
  - [1. Synthetic Data Generation](#1-synthetic-data-generation)
  - [2. SQL ETL Pipeline](#2-sql-etl-pipeline)
  - [3. NLTK VADER Sentiment Engine](#3-nltk-vader-sentiment-engine)
  - [4. Customer Voice Analysis Engine](#4-customer-voice-analysis-engine)
  - [5. Campaign Analytics](#5-campaign-analytics)
- [Dashboard](#dashboard)
- [Key Metrics & Outcomes](#key-metrics--outcomes)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Design Decisions](#design-decisions)

---

## Project Overview

Built an **end-to-end analytics pipeline** that:

- **Analyzed 600+ customer reviews** using NLTK VADER and Pandas, classifying each into Positive / Negative / Neutral
- **Spotted product spikes** — Ski Boots saw a **+150% review volume surge** during winter season campaigns
- **Tracked conversion rebound** from **5.0% → 18.5%** and **15.4% CTR** to guide campaign optimization and retention strategy
- **Extracted customer voice** — themes, aspect-based sentiment, pain points with actionable recommendations, and NPS-style customer segmentation

This project demonstrates a realistic data analytics workflow: raw data ingestion → SQL-driven cleaning → NLP sentiment scoring → business insights → interactive dashboard.

---

## Architecture & Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  generate_data   │────▶│   SQLite DB      │────▶│   etl_pipeline   │
│  (Faker, 700     │     │   (raw_reviews,  │     │   (CTEs,         │
│   synthetic      │     │    campaigns)    │     │    ROW_NUMBER,   │
│   reviews)       │     │                  │     │    COALESCE)     │
└──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                           │
                              cleaned_reviews              │
                         ┌─────────────────────────────────┘
                         ▼
          ┌──────────────────────┐     ┌──────────────────────────┐
          │  sentiment_engine    │────▶│  voice_analysis          │
          │  (NLTK VADER,       │     │  (Theme extraction,      │
          │   vectorized        │     │   Aspect sentiment,      │
          │   scoring)          │     │   Pain point mining,     │
          │                     │     │   NPS segmentation)      │
          └──────────────────────┘     └──────────┬───────────────┘
                                                  │
                                                  ▼
                                    ┌──────────────────────┐
                                    │  Flask Dashboard     │
                                    │  (3 tabs, filters,   │
                                    │   Chart.js, CSV      │
                                    │   export)            │
                                    └──────────────────────┘
```

The orchestrator (`run_pipeline.py`) executes all 5 stages sequentially in ~1.5 seconds.

---

## Data Store

All data lives in a **SQLite database** at `data/campaign_voice.db`. The schema has 9 tables:

| Table | Records | Purpose |
|-------|---------|---------|
| `raw_reviews` | 700 | Unprocessed reviews with intentional duplicates & nulls |
| `cleaned_reviews` | 670 | Deduplicated, null-handled, sentiment-scored reviews |
| `campaigns` | 8 | Campaign metadata (impressions, clicks, conversions, spend) |
| `campaign_metrics` | 39 | Aggregated per-campaign sentiment + conversion metrics |
| `review_themes` | 58 | NLP-extracted themes with mention counts and sentiment |
| `aspect_sentiment` | 50 | Product × attribute sentiment scores |
| `pain_points` | 10 | Ranked pain points with recommended actions |
| `customer_segments` | 3 | NPS-style segments (Promoter / Passive / Detractor) |
| `keyword_frequency` | 379+ | Unigram + bigram frequency analysis |

### Schema DDL

The schema is defined in `sql/01_create_tables.sql`. Key design:

```sql
CREATE TABLE IF NOT EXISTS cleaned_reviews (
    review_id       INTEGER PRIMARY KEY,
    customer_name   TEXT,
    product_name    TEXT NOT NULL,
    product_category TEXT,
    review_text     TEXT NOT NULL,
    rating          INTEGER CHECK(rating BETWEEN 1 AND 5),
    review_date     TEXT,
    source          TEXT,
    campaign_id     INTEGER,
    sentiment_compound REAL,     -- VADER compound: -1.0 to +1.0
    sentiment_pos   REAL,        -- Positive probability
    sentiment_neg   REAL,        -- Negative probability
    sentiment_neu   REAL,        -- Neutral probability
    sentiment_label TEXT,        -- 'Positive' | 'Negative' | 'Neutral'
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
);
```

---

## How to Run

### Prerequisites

- Python 3.10+
- pip

### Quick Start

```bash
# 1. Install dependencies
pip install flask pandas nltk faker

# 2. Run the full pipeline (generates data + cleans + sentiment + voice analysis)
python run_pipeline.py

# 3. Launch the dashboard
python app.py

# 4. Open browser
# http://localhost:5000
```

### On Windows (if unicode errors):

```powershell
$env:PYTHONIOENCODING='utf-8'
python run_pipeline.py
python app.py
```

### CSV Data Export

The dashboard provides 4 export options:
- **Export Reviews CSV** — All 670 cleaned reviews with sentiment scores
- **Export Campaigns CSV** — 8 campaigns with impressions, clicks, CTR, conversions, spend
- **Export Voice CSV** — Pain points, themes, aspects, segments
- **Download All (ZIP)** — Complete dataset as a ZIP file with one CSV per table

You can also export **filtered** results from the Sentiment tab using the "Export Filtered CSV" button.

---

## Pipeline Deep Dive

### 1. Synthetic Data Generation

**File:** `generate_data.py`

Generates 700 realistic customer reviews across 6 outdoor gear products using the Faker library. The generator creates:

- **Intentional duplicates** (30 reviews) — to demonstrate ETL dedup capability
- **Null customer names** (~10%) — to demonstrate COALESCE handling
- **Season-weighted distribution** — Ski Boots reviews spike 3x in winter months
- **Realistic review text** — Product-specific templates with attribute-based sentiment variation
- **8 marketing campaigns** spanning Fall 2024 → Winter 2025

```python
# Weighted seasonal distribution ensures Ski Boots spike in winter
SEASONAL_WEIGHTS = {
    'Alpine Pro Ski Boots': {'Winter': 3.0, 'Fall': 1.5, 'Spring': 0.3, 'Summer': 0.2},
    'TrailBlazer Running Shoes': {'Summer': 2.5, 'Spring': 2.0, 'Fall': 1.0, 'Winter': 0.3},
    ...
}
```

### 2. SQL ETL Pipeline

**Files:** `etl_pipeline.py`, `sql/02_clean_data.sql`, `sql/03_analytics.sql`

The ETL stage demonstrates three key SQL techniques:

#### CTEs (Common Table Expressions)

Used to chain deduplication → null handling → final insert in a single readable query:

```sql
WITH deduplicated AS (
    -- Assign row numbers partitioned by (customer, product, review_text)
    -- to identify and remove exact duplicate reviews
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_name, product_name, review_text
            ORDER BY review_date DESC
        ) AS rn
    FROM raw_reviews
),
cleaned AS (
    SELECT
        review_id,
        COALESCE(customer_name, 'Anonymous') AS customer_name,
        COALESCE(product_name, 'Unknown Product') AS product_name,
        ...
    FROM deduplicated
    WHERE rn = 1   -- Keep only the first occurrence
)
INSERT OR REPLACE INTO cleaned_reviews SELECT ... FROM cleaned;
```

#### ROW_NUMBER() Window Function

Partitions reviews by `(customer_name, product_name, review_text)` and numbers each partition. Row number = 1 is kept, duplicates are discarded. Result: **700 → 670 reviews** (30 duplicates removed).

#### COALESCE for Null Handling

Replaces NULL values with sensible defaults:
- `COALESCE(customer_name, 'Anonymous')` — 64 null names handled
- `COALESCE(product_name, 'Unknown Product')`
- `COALESCE(rating, 3)` — Default to neutral rating

#### LAG Window Function

Used in `03_analytics.sql` to compute period-over-period review volume change:

```sql
LAG(total_reviews) OVER (
    PARTITION BY product_name
    ORDER BY campaign_id
) AS prev_reviews
```

This enables calculating the **+150% Ski Boots spike** by comparing current vs previous period volume.

### 3. NLTK VADER Sentiment Engine

**File:** `sentiment_engine.py`

Uses the VADER (Valence Aware Dictionary and sEntiment Reasoner) lexicon-based sentiment analyzer from NLTK. VADER is specifically tuned for social media and customer review text.

```python
from nltk.sentiment.vader import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()

def classify(compound_score):
    """Classify compound score into sentiment label."""
    if compound_score >= 0.05:
        return 'Positive'
    elif compound_score <= -0.05:
        return 'Negative'
    return 'Neutral'

# Vectorized scoring using Pandas
df['scores'] = df['review_text'].apply(lambda x: sia.polarity_scores(x))
df['sentiment_compound'] = df['scores'].apply(lambda x: x['compound'])
df['sentiment_pos'] = df['scores'].apply(lambda x: x['pos'])
df['sentiment_neg'] = df['scores'].apply(lambda x: x['neg'])
df['sentiment_label'] = df['sentiment_compound'].apply(classify)
```

**Why VADER?**
- No training data required (lexicon-based)
- Handles intensifiers ("very good"), negations ("not bad"), punctuation ("great!!!")
- Returns a compound score from -1.0 (most negative) to +1.0 (most positive)
- Fast: processes 670 reviews in <0.5 seconds

**Output Distribution (typical run):**
| Label | Count | % |
|-------|-------|---|
| Positive | ~460 | 68.7% |
| Negative | ~170 | 25.4% |
| Neutral | ~40 | 6.0% |

### 4. Customer Voice Analysis Engine

**File:** `voice_analysis.py`

The most complex module — extracts 5 types of insights from customer reviews:

#### a) Theme Extraction

Uses keyword matching against a curated taxonomy of 20+ product-relevant themes (durability, comfort, warmth, fit, price, etc.). Each review is scanned for theme mentions, then aggregated by product with average sentiment.

```python
THEME_TAXONOMY = {
    'durability': ['durable', 'durability', 'lasted', 'wear', 'tear', 'broke', 'broken'],
    'comfort': ['comfortable', 'comfort', 'cushion', 'padding', 'cozy', 'snug'],
    'warmth': ['warm', 'warmth', 'insulation', 'cold', 'freezing', 'toasty'],
    ...
}

for theme, keywords in THEME_TAXONOMY.items():
    mask = df['review_lower'].apply(lambda x: any(kw in x for kw in keywords))
    matches = df[mask]
    if len(matches) > 0:
        themes.append({
            'theme': theme,
            'mention_count': len(matches),
            'avg_sentiment': matches['sentiment_compound'].mean()
        })
```

#### b) Aspect-Based Sentiment

Groups reviews by product × attribute, calculates positive/negative/neutral mention counts and average compound score. Also extracts sample verbatim quotes for each polarity.

#### c) Pain Point Mining

Scans negative reviews (compound < -0.05) for specific pain-point patterns using regex:

```python
PAIN_PATTERNS = {
    'overpriced': r'\b(overpriced|expensive|not worth|rip.?off|waste of money)\b',
    'durability issues': r'\b(broke|broken|fell apart|peeling|cracked|worn out)\b',
    'runs small': r'\b(too tight|runs small|sizing|size up|narrow)\b',
    'too heavy': r'\b(heavy|bulky|weighs? a ton|carrying bricks)\b',
    ...
}
```

Each pain point gets an auto-generated **recommended action** for campaign optimization (e.g., "Add price comparison chart vs competitors").

#### d) Keyword Frequency

Uses NLTK tokenization and FreqDist for unigram + bigram frequency analysis:

```python
from nltk import word_tokenize, FreqDist, bigrams
from nltk.corpus import stopwords

tokens = word_tokenize(all_text.lower())
tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
unigram_freq = FreqDist(tokens)
bigram_freq = FreqDist(bigrams(tokens))
```

#### e) NPS-Style Customer Segmentation

Segments customers into Promoters / Passives / Detractors based on rating + sentiment:

```python
# Segmentation rules
conditions = [
    (df['rating'] >= 4) & (df['sentiment_compound'] > 0.2),   # Promoter
    (df['rating'] >= 3) & (df['sentiment_compound'] > -0.1),  # Passive
]
labels = ['Promoter', 'Passive']
df['segment'] = np.select(conditions, labels, default='Detractor')
```

### 5. Campaign Analytics

**File:** `sql/03_analytics.sql`

Joins sentiment data with campaign performance to compute aggregated metrics per campaign:

```sql
WITH review_agg AS (
    SELECT campaign_id, product_name, COUNT(*) AS total_reviews,
           AVG(sentiment_compound) AS avg_sentiment,
           ROUND(100.0 * SUM(CASE WHEN sentiment_label='Positive' THEN 1 ELSE 0 END) / COUNT(*), 1) AS positive_pct
    FROM cleaned_reviews WHERE campaign_id IS NOT NULL
    GROUP BY campaign_id, product_name
),
volume_change AS (
    SELECT campaign_id, product_name, total_reviews,
           LAG(total_reviews) OVER (PARTITION BY product_name ORDER BY campaign_id) AS prev_reviews,
           ...
    FROM review_agg
)
INSERT OR REPLACE INTO campaign_metrics ...
```

---

## Dashboard

### Three interactive tabs:

**Tab 1 — Campaign Sentiment:**
- 6 KPI cards (reviews, avg sentiment, positive %, negative %, best CTR, peak conversion)
- 5 interactive filters (Product, Sentiment, Season, Source, Rating)
- Sentiment distribution doughnut chart
- Product sentiment horizontal bar chart
- Ski Boots +150% volume spike line chart
- Conversion rebound (5.0% → 18.5%) area chart
- Campaign performance grouped bar chart
- Seasonal sentiment bar chart
- Paginated reviews table with search

**Tab 2 — Customer Voice:**
- Voice KPIs (top theme, #1 pain point, promoter %, detractor %)
- Theme word cloud (sized by frequency, colored by sentiment)
- Aspect sentiment matrix (product × attribute heatmap)
- Love vs. Hate panels with verbatim customer quotes
- Pain point tracker with frequency bars and recommended actions
- NPS-style customer segment cards + stacked bar
- Actionable campaign insight cards

**Tab 3 — Data Explorer:**
- Full searchable table of all 670 reviews
- Campaign metrics table
- Voice analysis summary table
- CSV + ZIP download buttons

All charts are rendered with **Chart.js** and recompute dynamically when filters change.

---

## Key Metrics & Outcomes

| Metric | Value | How It Was Derived |
|--------|-------|--------------------|
| Reviews Analyzed | 670 | After ETL dedup of 700 raw reviews |
| Ski Boots Volume Spike | +150% | Winter vs. pre-winter review count (LAG window function) |
| Conversion Rebound | 5.0% → 18.5% | Winter Kickoff (5.0%) → Ski Season Blitz (18.5%) |
| Best CTR | 15.4% | Ski Season Blitz: 13,090 clicks / 85,000 impressions |
| Avg Sentiment | 0.333 | VADER compound across all cleaned reviews |
| Positive % | 68.7% | 460 / 670 reviews classified positive |
| Pain Points Found | 10 | Regex mining on negative reviews |
| NPS Promoters | 50.7% | Rating ≥ 4 AND sentiment > 0.2 |

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Data Store | SQLite | Zero-config, file-based, perfect for portfolio projects |
| ETL | SQL (CTEs, Window Functions) | Demonstrates advanced SQL skills employers look for |
| Sentiment | NLTK VADER | Lexicon-based, no training needed, handles review text well |
| NLP | NLTK (tokenize, FreqDist, ngrams) | Standard NLP toolkit for keyword/topic analysis |
| DataFrames | Pandas | Industry-standard for data manipulation in Python |
| Synthetic Data | Faker | Generates realistic names, dates, patterns |
| Backend | Flask | Lightweight Python web framework |
| Charts | Chart.js 4.x | Client-side, responsive, well-documented |
| Design | Apple-inspired white theme | Clean, professional, high-readability |

---

## Project Structure

```
Campaign Sentiment & Customer Voice Analysis/
├── app.py                          # Flask web app (routes + API + CSV export)
├── generate_data.py                # Synthetic data generator (700 reviews + 8 campaigns)
├── etl_pipeline.py                 # SQL ETL: CTEs, ROW_NUMBER, COALESCE, LAG
├── sentiment_engine.py             # NLTK VADER sentiment analysis
├── voice_analysis.py               # Customer Voice: themes, aspects, pain points, segments
├── run_pipeline.py                 # Pipeline orchestrator (runs all 5 stages)
├── requirements.txt                # Python dependencies
├── README.md                       # This documentation
│
├── data/
│   └── campaign_voice.db           # SQLite database (generated by pipeline)
│
├── sql/
│   ├── 01_create_tables.sql        # Schema DDL (9 tables)
│   ├── 02_clean_data.sql           # ETL: dedup + null handling + cleaning
│   └── 03_analytics.sql            # Analytics: LAG, aggregations, campaign metrics
│
├── static/
│   ├── css/
│   │   └── style.css               # Apple white theme (clean, minimal)
│   └── js/
│       └── dashboard.js            # Chart.js charts + filters + CSV export
│
└── templates/
    └── dashboard.html              # Dashboard HTML (3 tabs, 15+ widgets)
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **SQLite** over PostgreSQL | Zero-config, ships as a single file, no setup friction for reviewers |
| **VADER** over fine-tuned models | No training data needed; accurate for review text; deterministic outputs |
| **Synthetic data** over real data | No privacy concerns; controllable distributions; reproducible results |
| **30 intentional duplicates** | Demonstrates ETL dedup capability (ROW_NUMBER partitioning) |
| **Client-side filtering** | All 670 reviews sent to browser; filters, charts, and tables update instantly without server roundtrips |
| **White Apple theme** | Maximum readability; professional portfolio appearance; employer-friendly |
| **3-tab layout** | Separates macro (Sentiment) from qualitative (Voice) from raw (Explorer) to avoid information overload |
| **CSV export** | Lets reviewers independently verify the data and analysis |
