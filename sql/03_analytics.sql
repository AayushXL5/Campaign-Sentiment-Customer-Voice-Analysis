-- ============================================================
-- Analytics Queries: Window Functions, Aggregations, Campaign Metrics
-- Generates campaign_metrics from cleaned_reviews + campaigns
-- ============================================================

-- Build campaign metrics with sentiment aggregations and review volume changes
WITH review_agg AS (
    SELECT
        cr.campaign_id,
        cr.product_name,
        COUNT(*) AS total_reviews,
        AVG(cr.sentiment_compound) AS avg_sentiment,
        ROUND(100.0 * SUM(CASE WHEN cr.sentiment_label = 'Positive' THEN 1 ELSE 0 END) / COUNT(*), 1) AS positive_pct,
        ROUND(100.0 * SUM(CASE WHEN cr.sentiment_label = 'Negative' THEN 1 ELSE 0 END) / COUNT(*), 1) AS negative_pct
    FROM cleaned_reviews cr
    WHERE cr.campaign_id IS NOT NULL
    GROUP BY cr.campaign_id, cr.product_name
),
campaign_data AS (
    SELECT
        c.campaign_id,
        c.campaign_name,
        c.product_category,
        c.season,
        c.impressions,
        c.clicks,
        c.conversions,
        ROUND(100.0 * c.clicks / NULLIF(c.impressions, 0), 1) AS ctr,
        ROUND(100.0 * c.conversions / NULLIF(c.clicks, 0), 1) AS conversion_rate
    FROM campaigns c
),
volume_change AS (
    -- Calculate review volume change using LAG window function
    SELECT
        campaign_id,
        product_name,
        total_reviews,
        LAG(total_reviews) OVER (
            PARTITION BY product_name 
            ORDER BY campaign_id
        ) AS prev_reviews,
        CASE 
            WHEN LAG(total_reviews) OVER (PARTITION BY product_name ORDER BY campaign_id) IS NOT NULL
            THEN ROUND(
                100.0 * (total_reviews - LAG(total_reviews) OVER (PARTITION BY product_name ORDER BY campaign_id))
                / NULLIF(LAG(total_reviews) OVER (PARTITION BY product_name ORDER BY campaign_id), 0),
                1
            )
            ELSE 0.0
        END AS review_volume_change_pct
    FROM review_agg
)
INSERT OR REPLACE INTO campaign_metrics (
    campaign_id, campaign_name, product_category, season,
    total_reviews, avg_sentiment, positive_pct, negative_pct,
    ctr, conversion_rate, review_volume_change_pct
)
SELECT
    cd.campaign_id,
    cd.campaign_name,
    cd.product_category,
    cd.season,
    COALESCE(ra.total_reviews, 0),
    COALESCE(ra.avg_sentiment, 0),
    COALESCE(ra.positive_pct, 0),
    COALESCE(ra.negative_pct, 0),
    cd.ctr,
    cd.conversion_rate,
    COALESCE(vc.review_volume_change_pct, 0)
FROM campaign_data cd
LEFT JOIN review_agg ra ON cd.campaign_id = ra.campaign_id
LEFT JOIN volume_change vc ON cd.campaign_id = vc.campaign_id
    AND ra.product_name = vc.product_name;


-- ============================================================
-- Additional Analytics Views using Window Functions
-- ============================================================

-- Sentiment trend over time with running average
-- (Used by dashboard for trend charts)
-- SELECT
--     review_date,
--     product_name,
--     sentiment_compound,
--     AVG(sentiment_compound) OVER (
--         PARTITION BY product_name
--         ORDER BY review_date
--         ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
--     ) AS sentiment_7day_avg,
--     ROW_NUMBER() OVER (
--         PARTITION BY product_name
--         ORDER BY review_date DESC
--     ) AS recency_rank
-- FROM cleaned_reviews
-- ORDER BY product_name, review_date;

-- Conversion trend with LAG for period-over-period comparison
-- SELECT
--     campaign_id,
--     campaign_name,
--     season,
--     conversion_rate,
--     LAG(conversion_rate) OVER (ORDER BY campaign_id) AS prev_conversion_rate,
--     conversion_rate - COALESCE(LAG(conversion_rate) OVER (ORDER BY campaign_id), 0) AS conversion_change
-- FROM campaign_metrics
-- ORDER BY campaign_id;
