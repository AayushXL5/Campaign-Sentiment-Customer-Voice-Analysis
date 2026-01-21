"""
Sentiment Engine — NLTK VADER sentiment analysis on cleaned reviews.
Computes compound, pos, neg, neu scores and classifies sentiment.
"""

import sqlite3
import os
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download VADER lexicon (silent if already present)
nltk.download('vader_lexicon', quiet=True)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'campaign_voice.db')


def analyze_sentiment():
    """Run VADER sentiment analysis on all cleaned reviews."""
    conn = sqlite3.connect(DB_PATH)

    # Load cleaned reviews into Pandas DataFrame
    df = pd.read_sql_query("SELECT id, review_id, review_text FROM cleaned_reviews", conn)
    print(f"  Analyzing {len(df)} reviews with NLTK VADER...")

    # Initialize VADER
    sia = SentimentIntensityAnalyzer()

    # Compute sentiment scores
    sentiments = df['review_text'].apply(lambda text: sia.polarity_scores(str(text)))
    df['sentiment_compound'] = sentiments.apply(lambda x: x['compound'])
    df['sentiment_pos'] = sentiments.apply(lambda x: x['pos'])
    df['sentiment_neg'] = sentiments.apply(lambda x: x['neg'])
    df['sentiment_neu'] = sentiments.apply(lambda x: x['neu'])

    # Classify sentiment
    def classify(compound):
        if compound >= 0.05:
            return 'Positive'
        elif compound <= -0.05:
            return 'Negative'
        else:
            return 'Neutral'

    df['sentiment_label'] = df['sentiment_compound'].apply(classify)

    # Update database
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            UPDATE cleaned_reviews
            SET sentiment_compound = ?,
                sentiment_pos = ?,
                sentiment_neg = ?,
                sentiment_neu = ?,
                sentiment_label = ?
            WHERE id = ?
        """, (row['sentiment_compound'], row['sentiment_pos'],
              row['sentiment_neg'], row['sentiment_neu'],
              row['sentiment_label'], row['id']))

    conn.commit()

    # Summary
    label_counts = df['sentiment_label'].value_counts()
    total = len(df)
    print(f"  ✓ Sentiment analysis complete:")
    print(f"    → Positive: {label_counts.get('Positive', 0)} ({100*label_counts.get('Positive', 0)/total:.1f}%)")
    print(f"    → Negative: {label_counts.get('Negative', 0)} ({100*label_counts.get('Negative', 0)/total:.1f}%)")
    print(f"    → Neutral:  {label_counts.get('Neutral', 0)} ({100*label_counts.get('Neutral', 0)/total:.1f}%)")
    print(f"    → Avg compound score: {df['sentiment_compound'].mean():.4f}")

    conn.close()
    return df


if __name__ == '__main__':
    print("=" * 60)
    print("Sentiment Engine — NLTK VADER")
    print("=" * 60)
    analyze_sentiment()
