-- ============================================================
-- ETL Pipeline: Data Cleaning with CTEs, Window Functions, COALESCE
-- Deduplicates raw_reviews, handles nulls, normalizes dates
-- ============================================================

-- Step 1: Deduplicate and clean raw reviews using CTEs + Window Functions
WITH deduplicated AS (
    -- Use ROW_NUMBER to identify duplicate review_ids, keeping the first occurrence
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY review_id 
            ORDER BY id ASC
        ) AS rn
    FROM raw_reviews
),
cleaned AS (
    -- Apply COALESCE for null handling, filter to first occurrence only
    SELECT
        review_id,
        COALESCE(customer_name, 'Anonymous') AS customer_name,
        COALESCE(product_name, 'Unknown Product') AS product_name,
        COALESCE(product_category, 'Uncategorized') AS product_category,
        COALESCE(review_text, '') AS review_text,
        COALESCE(rating, 3) AS rating,
        COALESCE(review_date, DATE('now')) AS review_date,
        COALESCE(source, 'Unknown') AS source,
        campaign_id,
        COALESCE(is_verified_purchase, 0) AS is_verified_purchase
    FROM deduplicated
    WHERE rn = 1
        AND COALESCE(review_text, '') != ''
),
ranked AS (
    -- Rank reviews per product by date (most recent first)
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_name 
            ORDER BY review_date DESC
        ) AS product_rank
    FROM cleaned
)
INSERT OR REPLACE INTO cleaned_reviews (
    review_id, customer_name, product_name, product_category,
    review_text, rating, review_date, source, campaign_id, row_rank
)
SELECT
    review_id, customer_name, product_name, product_category,
    review_text, rating, review_date, source, campaign_id, product_rank
FROM ranked;
