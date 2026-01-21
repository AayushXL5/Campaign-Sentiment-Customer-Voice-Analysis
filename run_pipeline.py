"""
Pipeline Orchestrator — Runs the complete data pipeline end-to-end:
  1. Generate synthetic data (650+ reviews + campaigns)
  2. Run SQL ETL (CTEs, Window Functions, COALESCE)
  3. Run VADER sentiment analysis
  4. Run Customer Voice analysis (themes, aspects, pain points, segments)
  5. Run analytics SQL (campaign metrics)
"""

import time
from generate_data import populate_database
from etl_pipeline import run_etl, run_analytics
from sentiment_engine import analyze_sentiment
from voice_analysis import run_voice_analysis


def run_full_pipeline():
    """Execute the complete pipeline."""
    print("=" * 70)
    print("  Campaign Sentiment & Customer Voice Analysis")
    print("  Full Pipeline Execution")
    print("=" * 70)
    start = time.time()

    # Step 1: Generate Data
    print("\n[1/5] Generating synthetic data...")
    populate_database()

    # Step 2: Run ETL
    print("\n[2/5] Running SQL ETL pipeline...")
    clean_count = run_etl()

    # Step 3: Sentiment Analysis
    print("\n[3/5] Running NLTK VADER sentiment analysis...")
    analyze_sentiment()

    # Step 4: Customer Voice Analysis
    print("\n[4/5] Running Customer Voice analysis...")
    run_voice_analysis()

    # Step 5: Campaign Analytics
    print("\n[5/5] Running campaign analytics...")
    run_analytics()

    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print(f"  ✓ Pipeline complete in {elapsed:.1f}s")
    print(f"  ✓ Dashboard ready — run: python app.py")
    print("=" * 70)


if __name__ == '__main__':
    run_full_pipeline()
