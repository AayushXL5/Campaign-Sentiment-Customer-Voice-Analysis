"""
Customer Voice Analysis Engine
Extracts themes, aspect-based sentiment, pain points, keywords, and customer segments.
Goes beyond sentiment scores to capture WHAT customers are saying.
"""

import sqlite3
import os
import json
import re
from collections import Counter, defaultdict
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk import ngrams

# Download required NLTK data
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('vader_lexicon', quiet=True)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'campaign_voice.db')

# ── Theme taxonomy ──────────────────────────────────────────────────────────
THEME_TAXONOMY = {
    'Product Quality': ['durability', 'durable', 'material', 'stitching', 'construction',
                        'build', 'quality', 'built', 'craftsmanship', 'fell apart',
                        'peeling', 'broke', 'breaks', 'flimsy', 'solid', 'robust', 'sturdy'],
    'Comfort & Fit': ['fit', 'fits', 'sizing', 'size', 'comfort', 'comfortable',
                      'cushioning', 'cushion', 'snug', 'tight', 'loose', 'blisters',
                      'pressure', 'padding', 'break-in', 'true to size', 'runs small',
                      'runs large', 'hot spots', 'discomfort'],
    'Performance': ['warmth', 'warm', 'insulation', 'waterproof', 'waterproofing',
                    'breathability', 'breathable', 'grip', 'traction', 'support',
                    'ankle support', 'ventilation', 'airflow', 'sweat', 'dry',
                    'rain', 'cold', 'heat', 'slippery', 'reliable', 'ignite'],
    'Value': ['price', 'value', 'worth', 'money', 'expensive', 'overpriced',
              'cheap', 'affordable', 'premium', 'cost', 'budget', 'dollar',
              'markup', 'penny', 'fair price'],
    'Service': ['shipping', 'delivery', 'return', 'returns', 'customer service',
                'packaging', 'exchange', 'warranty', 'refund', 'support team',
                'helpful', 'unhelpful', 'response'],
}

# ── Aspect definitions per product type ─────────────────────────────────────
ASPECT_KEYWORDS = {
    'fit': ['fit', 'fits', 'sizing', 'size', 'true to size', 'runs small', 'runs large',
            'snug', 'tight', 'loose', 'toe box', 'half a size'],
    'comfort': ['comfort', 'comfortable', 'cushioning', 'cushion', 'padding',
                'blisters', 'hot spots', 'pressure points', 'discomfort',
                'all-day', 'wore them'],
    'durability': ['durability', 'durable', 'built', 'tank', 'wear', 'stitching',
                   'fell apart', 'peeling', 'broke', 'season', 'miles', 'construction'],
    'warmth': ['warmth', 'warm', 'toasty', 'insulation', 'freezing', 'cold',
               'heat', 'temperature', 'thermal'],
    'weight': ['weight', 'lightweight', 'light', 'heavy', 'bulky', 'bricks',
               'ultralight', 'portable', 'compact', 'packable'],
    'price': ['price', 'value', 'money', 'worth', 'expensive', 'overpriced',
              'cheap', 'premium', 'dollar', 'penny', 'cost', 'affordable'],
    'grip': ['grip', 'traction', 'slippery', 'slipped', 'tread', 'sole',
             'wet', 'rocks', 'terrain', 'downhill'],
    'waterproofing': ['waterproof', 'waterproofing', 'rain', 'dry', 'leak',
                      'leaked', 'moisture', 'seepage', 'torrential', 'soaked'],
    'breathability': ['breathability', 'breathable', 'airflow', 'ventilation',
                      'sweat', 'cool', 'plastic bags'],
    'safety': ['safety', 'safe', 'secure', 'buckle', 'confidence', 'jammed',
               'flimsy', 'mechanism'],
    'reliability': ['reliable', 'reliability', 'failed', 'ignite', 'unreliable',
                    'consistent', 'every time', 'stopped working'],
    'ease of use': ['easy', 'intuitive', 'minutes', 'complicated', 'instructions',
                    'figure out', 'practice', 'set up', 'setup'],
    'capacity': ['capacity', 'space', 'compartment', 'pockets', 'fits everything',
                 'too small', 'essentials', 'day trips'],
    'portability': ['portable', 'compact', 'packable', 'bulky', 'space', 'weighs'],
    'fuel efficiency': ['fuel', 'canister', 'burn', 'economy', 'efficient'],
    'ankle support': ['ankle', 'support', 'locked', 'cuff', 'twisted', 'rigidity'],
}

# ── Pain point patterns ─────────────────────────────────────────────────────
PAIN_POINT_PATTERNS = {
    'runs small': r'runs?\s+small|too\s+tight|size\s+up|sizing\s+(chart\s+)?inaccurate',
    'poor insulation': r'freezing|cold|thin\s+insulation|no\s+warmth|zero\s+warmth',
    'durability issues': r'fell\s+apart|broke|peeling|stitching\s+came|poor\s+quality|flimsy',
    'uncomfortable': r'blisters|pressure\s+points|uncomfortable|discomfort|hot\s+spots',
    'overpriced': r'overpriced|too\s+expensive|not\s+worth|save\s+your\s+money|half\s+the\s+price',
    'poor grip': r'slippery|no\s+grip|zero\s+grip|lost\s+traction|dangerous',
    'leaks': r'leaked|soaked|moisture|not\s+waterproof|leaks',
    'not breathable': r'sweat|no\s+breathability|zero\s+breathability|plastic\s+bags',
    'too heavy': r'too\s+heavy|bricks|bulky|weighs\s+a\s+ton',
    'unreliable': r'failed|unreliable|stopped\s+working|jammed',
}

PAIN_POINT_ACTIONS = {
    'runs small': 'Add detailed sizing guide with measurement chart to campaign landing page',
    'poor insulation': 'Highlight insulation technology specs in ad creative; add warmth rating badge',
    'durability issues': 'Feature warranty/guarantee prominently in campaign; add durability test video',
    'uncomfortable': 'Include customer comfort testimonials in ads; offer break-in period tips',
    'overpriced': 'Add price comparison chart vs competitors; highlight value proposition in copy',
    'poor grip': 'Add terrain-specific performance data to product pages; feature grip test content',
    'leaks': 'Showcase waterproof testing footage in campaigns; add water resistance rating',
    'not breathable': 'Add breathability technology explanation; include climate-specific recommendations',
    'too heavy': 'Compare weight specs vs competitors; highlight weight-to-performance ratio',
    'unreliable': 'Add reliability guarantee; feature endurance testing in campaign content',
}


def run_voice_analysis():
    """Run the complete Customer Voice Analysis pipeline."""
    conn = sqlite3.connect(DB_PATH)
    sia = SentimentIntensityAnalyzer()

    # Load cleaned reviews with sentiment
    df = pd.read_sql_query("""
        SELECT id, review_id, review_text, product_name, product_category,
               rating, sentiment_compound, sentiment_label, review_date
        FROM cleaned_reviews
        WHERE review_text IS NOT NULL AND review_text != ''
    """, conn)

    print(f"  Analyzing {len(df)} reviews for Customer Voice insights...")

    # Clear existing voice data
    cursor = conn.cursor()
    for table in ['review_themes', 'aspect_sentiment', 'pain_points', 'keyword_frequency', 'customer_segments']:
        cursor.execute(f"DELETE FROM {table}")

    # ── 1. Theme Extraction ──────────────────────────────────────────────
    print("  → Extracting themes and topics...")
    theme_data = defaultdict(lambda: {'count': 0, 'sentiments': [], 'products': Counter()})

    for _, row in df.iterrows():
        text_lower = row['review_text'].lower()
        for theme_cat, keywords in THEME_TAXONOMY.items():
            for keyword in keywords:
                if keyword in text_lower:
                    key = (keyword, theme_cat)
                    theme_data[key]['count'] += 1
                    theme_data[key]['sentiments'].append(row['sentiment_compound'])
                    theme_data[key]['products'][row['product_name']] += 1

    # Aggregate themes — group similar keywords, keep top themes
    aggregated_themes = {}
    for (theme, cat), data in theme_data.items():
        if data['count'] >= 3:  # Minimum mention threshold
            top_product = data['products'].most_common(1)[0][0] if data['products'] else None
            avg_sent = sum(data['sentiments']) / len(data['sentiments']) if data['sentiments'] else 0
            aggregated_themes[theme] = {
                'theme': theme,
                'category': cat,
                'count': data['count'],
                'avg_sentiment': round(avg_sent, 4),
                'product': top_product,
            }

    for theme_info in aggregated_themes.values():
        cursor.execute("""
            INSERT INTO review_themes (theme, theme_category, mention_count, avg_sentiment, product_name)
            VALUES (?, ?, ?, ?, ?)
        """, (theme_info['theme'], theme_info['category'], theme_info['count'],
              theme_info['avg_sentiment'], theme_info['product']))

    theme_count = len(aggregated_themes)
    print(f"    ✓ {theme_count} unique themes extracted")

    # ── 2. Aspect-Based Sentiment ────────────────────────────────────────
    print("  → Computing aspect-based sentiment...")
    products = df['product_name'].unique()
    aspect_results = []

    for product in products:
        product_reviews = df[df['product_name'] == product]
        for aspect, keywords in ASPECT_KEYWORDS.items():
            pos_mentions = 0
            neg_mentions = 0
            neu_mentions = 0
            compounds = []
            pos_samples = []
            neg_samples = []

            for _, row in product_reviews.iterrows():
                text_lower = row['review_text'].lower()
                if any(kw in text_lower for kw in keywords):
                    compounds.append(row['sentiment_compound'])
                    if row['sentiment_compound'] >= 0.05:
                        pos_mentions += 1
                        if len(pos_samples) < 3:
                            pos_samples.append(row['review_text'][:200])
                    elif row['sentiment_compound'] <= -0.05:
                        neg_mentions += 1
                        if len(neg_samples) < 3:
                            neg_samples.append(row['review_text'][:200])
                    else:
                        neu_mentions += 1

            total = pos_mentions + neg_mentions + neu_mentions
            if total >= 2:  # Minimum mentions
                avg_comp = sum(compounds) / len(compounds) if compounds else 0
                cursor.execute("""
                    INSERT INTO aspect_sentiment
                    (product_name, aspect, positive_mentions, negative_mentions,
                     neutral_mentions, avg_compound, sample_positive, sample_negative)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (product, aspect, pos_mentions, neg_mentions, neu_mentions,
                      round(avg_comp, 4),
                      pos_samples[0] if pos_samples else None,
                      neg_samples[0] if neg_samples else None))
                aspect_results.append((product, aspect, avg_comp))

    print(f"    ✓ {len(aspect_results)} product-aspect combinations analyzed")

    # ── 3. Pain Point Mining ─────────────────────────────────────────────
    print("  → Mining pain points from negative reviews...")
    negative_reviews = df[df['sentiment_compound'] <= -0.05]
    pain_point_data = defaultdict(lambda: {'count': 0, 'severities': [], 'verbatims': [], 'products': Counter()})

    for _, row in negative_reviews.iterrows():
        text_lower = row['review_text'].lower()
        for pp_name, pattern in PAIN_POINT_PATTERNS.items():
            if re.search(pattern, text_lower):
                pain_point_data[pp_name]['count'] += 1
                pain_point_data[pp_name]['severities'].append(abs(row['sentiment_compound']))
                pain_point_data[pp_name]['verbatims'].append(row['review_text'][:250])
                pain_point_data[pp_name]['products'][row['product_name']] += 1

    pp_count = 0
    for pp_name, data in sorted(pain_point_data.items(), key=lambda x: x[1]['count'], reverse=True):
        if data['count'] >= 2:
            avg_severity = sum(data['severities']) / len(data['severities'])
            top_product = data['products'].most_common(1)[0][0]
            cursor.execute("""
                INSERT INTO pain_points
                (product_name, pain_point, frequency, severity_score, sample_verbatim, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (top_product, pp_name, data['count'], round(avg_severity, 4),
                  data['verbatims'][0], PAIN_POINT_ACTIONS.get(pp_name, 'Review and address in next campaign cycle')))
            pp_count += 1

    print(f"    ✓ {pp_count} pain points identified with recommendations")

    # ── 4. Keyword Frequency Analysis ────────────────────────────────────
    print("  → Computing keyword frequencies...")
    try:
        stop_words = set(stopwords.words('english'))
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stop_words = set(stopwords.words('english'))

    custom_stops = stop_words | {'the', 'would', 'could', 'one', 'get', 'got', 'also',
                                  'much', 'even', 'really', 'like', 'just', 'every',
                                  'made', 'make', 'use', 'used', 'way', 'buy', 'bought',
                                  'n\'t', 'it\'s', '\'s', '``', '\'\'', '--'}

    all_words = []
    word_sentiments = defaultdict(list)

    for _, row in df.iterrows():
        try:
            tokens = word_tokenize(row['review_text'].lower())
            meaningful = [w for w in tokens if w.isalpha() and len(w) > 2 and w not in custom_stops]
            all_words.extend(meaningful)
            for w in set(meaningful):  # unique per review
                word_sentiments[w].append(row['sentiment_compound'])
        except Exception:
            continue

    # Unigrams
    word_freq = Counter(all_words)
    for word, freq in word_freq.most_common(80):
        avg_sent = sum(word_sentiments[word]) / len(word_sentiments[word]) if word_sentiments[word] else 0
        cursor.execute("""
            INSERT INTO keyword_frequency (keyword, frequency, avg_sentiment, product_name, is_bigram)
            VALUES (?, ?, ?, NULL, 0)
        """, (word, freq, round(avg_sent, 4)))

    # Bigrams
    bigram_words = []
    for _, row in df.iterrows():
        try:
            tokens = word_tokenize(row['review_text'].lower())
            meaningful = [w for w in tokens if w.isalpha() and len(w) > 2 and w not in custom_stops]
            bigram_words.extend([' '.join(bg) for bg in ngrams(meaningful, 2)])
        except Exception:
            continue

    bigram_freq = Counter(bigram_words)
    for bg, freq in bigram_freq.most_common(40):
        cursor.execute("""
            INSERT INTO keyword_frequency (keyword, frequency, avg_sentiment, product_name, is_bigram)
            VALUES (?, ?, 0, NULL, 1)
        """, (bg, freq))

    print(f"    ✓ {len(word_freq)} unigrams + {len(bigram_freq)} bigrams analyzed")

    # ── 5. Customer Segmentation (NPS-style) ─────────────────────────────
    print("  → Segmenting customers (Promoters / Passives / Detractors)...")

    def segment_customer(row):
        if row['rating'] >= 4 and row['sentiment_compound'] >= 0.05:
            return 'Promoter'
        elif row['rating'] <= 2 or row['sentiment_compound'] <= -0.05:
            return 'Detractor'
        else:
            return 'Passive'

    df['segment'] = df.apply(segment_customer, axis=1)
    total_customers = len(df)

    for segment_name in ['Promoter', 'Passive', 'Detractor']:
        seg_df = df[df['segment'] == segment_name]
        count = len(seg_df)

        if count == 0:
            continue

        avg_rating = seg_df['rating'].mean()
        avg_sent = seg_df['sentiment_compound'].mean()

        # Top themes for this segment
        seg_themes = Counter()
        for _, row in seg_df.iterrows():
            text_lower = row['review_text'].lower()
            for theme_cat, keywords in THEME_TAXONOMY.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        seg_themes[keyword] += 1

        top_themes = json.dumps([t[0] for t in seg_themes.most_common(5)])
        top_products = json.dumps(seg_df['product_name'].value_counts().head(3).index.tolist())
        pct = round(100.0 * count / total_customers, 1)

        cursor.execute("""
            INSERT OR REPLACE INTO customer_segments
            (segment_name, customer_count, avg_rating, avg_sentiment, top_themes, top_products, pct_of_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (segment_name, count, round(avg_rating, 2), round(avg_sent, 4),
              top_themes, top_products, pct))

        print(f"    → {segment_name}: {count} ({pct}%) | Avg Rating: {avg_rating:.1f} | Avg Sentiment: {avg_sent:.3f}")

    conn.commit()
    conn.close()
    print("  ✓ Customer Voice Analysis complete!")


if __name__ == '__main__':
    print("=" * 60)
    print("Customer Voice Analysis Engine")
    print("=" * 60)
    run_voice_analysis()
