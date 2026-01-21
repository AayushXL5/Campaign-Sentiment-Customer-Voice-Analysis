"""
ETL Pipeline — SQL-driven data cleaning with CTEs, Window Functions, COALESCE
Reads raw_reviews, deduplicates, cleans nulls, and populates cleaned_reviews.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'campaign_voice.db')


def run_etl():
    """Execute the SQL ETL pipeline."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql_dir = os.path.join(os.path.dirname(__file__), 'sql')

    # Step 1: Run the cleaning/dedup SQL
    print("  Running data cleaning (CTEs + ROW_NUMBER + COALESCE)...")
    with open(os.path.join(sql_dir, '02_clean_data.sql'), 'r') as f:
        sql = f.read()
        cursor.executescript(sql)

    conn.commit()

    # Verify results
    cursor.execute("SELECT COUNT(*) FROM raw_reviews")
    raw_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cleaned_reviews")
    clean_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM raw_reviews WHERE customer_name IS NULL")
    null_names = cursor.fetchone()[0]

    print(f"  ✓ Raw reviews: {raw_count}")
    print(f"  ✓ Cleaned reviews (after dedup): {clean_count}")
    print(f"  ✓ Null names handled via COALESCE: {null_names}")
    print(f"  ✓ Duplicates removed: {raw_count - clean_count}")

    conn.close()
    return clean_count


def run_analytics():
    """Execute the analytics SQL to populate campaign_metrics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql_dir = os.path.join(os.path.dirname(__file__), 'sql')

    print("  Running analytics (LAG, aggregations, campaign metrics)...")
    with open(os.path.join(sql_dir, '03_analytics.sql'), 'r') as f:
        full_sql = f.read()

    # Extract executable statements (skip full-line comments but keep inline ones)
    # Split on semicolons to get individual statements
    raw_blocks = full_sql.split(';')
    for block in raw_blocks:
        # Remove lines that are purely comments
        lines = block.split('\n')
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('--'):
                # Keep inline comments within a CTE (they provide context)
                # But skip if we haven't started any code yet
                if code_lines:
                    code_lines.append(line)
                continue
            code_lines.append(line)

        stmt = '\n'.join(code_lines).strip()
        if not stmt or all(l.strip().startswith('--') or l.strip() == '' for l in stmt.split('\n')):
            continue

        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"  Warning: {e}")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM campaign_metrics")
    metrics_count = cursor.fetchone()[0]
    print(f"  ✓ Campaign metrics generated: {metrics_count} rows")

    # Show key metrics
    cursor.execute("SELECT campaign_name, ctr, conversion_rate FROM campaign_metrics ORDER BY ctr DESC LIMIT 3")
    top = cursor.fetchall()
    for name, ctr, conv in top:
        print(f"    → {name}: CTR={ctr}%, Conv={conv}%")

    conn.close()
    return metrics_count


if __name__ == '__main__':
    print("=" * 60)
    print("ETL Pipeline")
    print("=" * 60)
    run_etl()
    print()
    run_analytics()
