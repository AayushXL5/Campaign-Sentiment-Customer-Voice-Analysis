-- ============================================================
-- Campaign Sentiment & Customer Voice Analysis
-- Schema DDL — Creates all raw and processed tables
-- ============================================================

-- Raw customer reviews (600+ records, may contain duplicates/nulls for ETL demo)
CREATE TABLE IF NOT EXISTS raw_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT,
    customer_name TEXT,
    product_name TEXT,
    product_category TEXT,
    review_text TEXT,
    rating INTEGER,
    review_date TEXT,
    source TEXT,
    campaign_id TEXT,
    is_verified_purchase INTEGER
);

-- Campaign performance data
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT,
    product_category TEXT,
    start_date TEXT,
    end_date TEXT,
    impressions INTEGER,
    clicks INTEGER,
    conversions INTEGER,
    spend REAL,
    season TEXT
);

-- Cleaned + deduplicated reviews (populated by ETL)
CREATE TABLE IF NOT EXISTS cleaned_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT UNIQUE,
    customer_name TEXT,
    product_name TEXT,
    product_category TEXT,
    review_text TEXT,
    rating INTEGER,
    review_date DATE,
    source TEXT,
    campaign_id TEXT,
    sentiment_compound REAL,
    sentiment_pos REAL,
    sentiment_neg REAL,
    sentiment_neu REAL,
    sentiment_label TEXT,
    row_rank INTEGER
);

-- Aggregated campaign metrics (populated by ETL + analytics)
CREATE TABLE IF NOT EXISTS campaign_metrics (
    campaign_id TEXT,
    campaign_name TEXT,
    product_category TEXT,
    season TEXT,
    total_reviews INTEGER,
    avg_sentiment REAL,
    positive_pct REAL,
    negative_pct REAL,
    ctr REAL,
    conversion_rate REAL,
    review_volume_change_pct REAL
);

-- Extracted themes/topics from reviews
CREATE TABLE IF NOT EXISTS review_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theme TEXT,
    theme_category TEXT,
    mention_count INTEGER,
    avg_sentiment REAL,
    product_name TEXT
);

-- Aspect-based sentiment per product attribute
CREATE TABLE IF NOT EXISTS aspect_sentiment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    aspect TEXT,
    positive_mentions INTEGER,
    negative_mentions INTEGER,
    neutral_mentions INTEGER,
    avg_compound REAL,
    sample_positive TEXT,
    sample_negative TEXT
);

-- Customer pain points from negative reviews
CREATE TABLE IF NOT EXISTS pain_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    pain_point TEXT,
    frequency INTEGER,
    severity_score REAL,
    sample_verbatim TEXT,
    recommended_action TEXT
);

-- Keyword frequency analysis
CREATE TABLE IF NOT EXISTS keyword_frequency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    frequency INTEGER,
    avg_sentiment REAL,
    product_name TEXT,
    is_bigram INTEGER
);

-- Customer segments (NPS-style)
CREATE TABLE IF NOT EXISTS customer_segments (
    segment_name TEXT PRIMARY KEY,
    customer_count INTEGER,
    avg_rating REAL,
    avg_sentiment REAL,
    top_themes TEXT,
    top_products TEXT,
    pct_of_total REAL
);
