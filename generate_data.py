"""
Synthetic Data Generator for Campaign Sentiment & Customer Voice Analysis
Generates 650+ realistic outdoor gear customer reviews and campaign data.
Designed to produce:
  - Ski Boots +150% review volume spike in winter
  - Conversion rebound from 5.0% to 18.5%
  - 15.4% CTR on best-performing campaign
  - Realistic sentiment distribution with seasonal patterns
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'campaign_voice.db')

# ── Product catalog ──────────────────────────────────────────────────────────
PRODUCTS = {
    'Alpine Pro Ski Boots': {
        'category': 'Footwear',
        'aspects': ['fit', 'warmth', 'durability', 'ankle support', 'weight', 'price'],
        'seasonal_weight': {'Winter': 5.0, 'Fall': 2.0, 'Spring': 0.8, 'Summer': 0.3},
    },
    'TrailBlazer Running Shoes': {
        'category': 'Footwear',
        'aspects': ['fit', 'comfort', 'grip', 'breathability', 'durability', 'price'],
        'seasonal_weight': {'Summer': 3.0, 'Spring': 2.5, 'Fall': 1.5, 'Winter': 0.5},
    },
    'Summit Hiking Backpack': {
        'category': 'Accessories',
        'aspects': ['comfort', 'capacity', 'durability', 'weight', 'waterproofing', 'price'],
        'seasonal_weight': {'Summer': 2.5, 'Spring': 2.0, 'Fall': 2.0, 'Winter': 1.0},
    },
    'ArcticShield Winter Jacket': {
        'category': 'Apparel',
        'aspects': ['warmth', 'fit', 'waterproofing', 'breathability', 'weight', 'price'],
        'seasonal_weight': {'Winter': 4.0, 'Fall': 2.5, 'Spring': 1.0, 'Summer': 0.2},
    },
    'VerticalEdge Climbing Harness': {
        'category': 'Equipment',
        'aspects': ['comfort', 'safety', 'durability', 'fit', 'weight', 'price'],
        'seasonal_weight': {'Summer': 2.5, 'Spring': 2.0, 'Fall': 1.5, 'Winter': 0.8},
    },
    'FlameKing Camp Stove': {
        'category': 'Equipment',
        'aspects': ['reliability', 'portability', 'fuel efficiency', 'durability', 'ease of use', 'price'],
        'seasonal_weight': {'Summer': 3.0, 'Spring': 2.0, 'Fall': 1.5, 'Winter': 1.0},
    },
}

SOURCES = ['Website', 'Mobile App', 'Social Media', 'Email Survey']

# ── Review templates (aspect-aware) ─────────────────────────────────────────
POSITIVE_TEMPLATES = [
    "Absolutely love the {aspect} on the {product}. {detail} Would buy again!",
    "The {aspect} is outstanding. {detail} Best purchase I've made this season.",
    "Really impressed with the {aspect}. {detail} Highly recommend for anyone serious about outdoor gear.",
    "Five stars for the {aspect}! {detail} Worth every penny.",
    "The {product} exceeded my expectations. The {aspect} is top-notch. {detail}",
    "Great {aspect}! {detail} Perfect for my {season} adventures.",
    "Can't say enough good things about the {aspect}. {detail} This is premium quality.",
    "After extensive testing, the {aspect} holds up beautifully. {detail} Very satisfied.",
    "The {aspect} is exactly what I needed. {detail} Solid build quality overall.",
    "Pleasantly surprised by the {aspect}. {detail} My go-to gear for {season}.",
]

NEGATIVE_TEMPLATES = [
    "Very disappointed with the {aspect}. {detail} Expected much better for the price.",
    "The {aspect} is a major letdown. {detail} Considering returning it.",
    "Not happy with the {aspect} at all. {detail} Would not recommend.",
    "The {product} has serious issues with {aspect}. {detail} Save your money.",
    "Terrible {aspect}. {detail} This does not live up to the brand's reputation.",
    "The {aspect} failed after just a few uses. {detail} Very poor quality.",
    "Really frustrated with the {aspect}. {detail} Customer service wasn't helpful either.",
    "The {aspect} is subpar. {detail} I've had much better from competitors.",
    "Wouldn't buy again due to the {aspect} issues. {detail} Not worth the premium price.",
    "The {aspect} completely ruined my {season} trip. {detail} Unacceptable quality.",
]

NEUTRAL_TEMPLATES = [
    "The {aspect} is decent but nothing special. {detail} Gets the job done.",
    "Average {aspect}. {detail} It's okay for casual use.",
    "The {aspect} is fine for the price point. {detail} Not bad, not great.",
    "Mixed feelings about the {aspect}. {detail} Could be improved.",
    "The {aspect} meets basic expectations. {detail} Nothing to write home about.",
]

# ── Aspect-specific detail fragments ─────────────────────────────────────────
ASPECT_DETAILS = {
    'fit': {
        'positive': ["True to size and very comfortable.", "Fits like a glove right out of the box.", "Perfect sizing with no break-in period needed."],
        'negative': ["Runs at least a full size small.", "The sizing chart is completely inaccurate.", "Way too tight around the toe box, even after sizing up."],
        'neutral': ["Sizing is a bit snug but manageable.", "Had to size up half a size."],
    },
    'warmth': {
        'positive': ["Kept my feet toasty in -20°C conditions.", "Incredible insulation technology.", "Even in deep powder, my feet stayed warm and dry."],
        'negative': ["My feet were freezing after just 30 minutes.", "The insulation is laughably thin.", "Zero warmth in actual cold weather."],
        'neutral': ["Adequate warmth for mild conditions.", "Okay in moderately cold weather."],
    },
    'comfort': {
        'positive': ["All-day comfort with zero hot spots.", "The cushioning system is phenomenal.", "Wore them for 12 hours straight with no discomfort."],
        'negative': ["Caused blisters on the very first use.", "Extremely uncomfortable pressure points.", "The padding wears out within weeks."],
        'neutral': ["Comfortable enough for short sessions.", "Takes some getting used to."],
    },
    'durability': {
        'positive': ["Built like a tank — no signs of wear after a full season.", "Exceptional build quality.", "Still going strong after hundreds of miles."],
        'negative': ["Fell apart within the first month.", "The stitching came undone after three uses.", "Material started peeling almost immediately."],
        'neutral': ["Seems durable enough, time will tell.", "Construction quality is average."],
    },
    'ankle support': {
        'positive': ["Incredible ankle support on steep terrain.", "The support system is top-tier.", "My ankles felt locked in and secure."],
        'negative': ["Virtually no ankle support.", "The ankle cuff is too loose.", "Twisted my ankle because the support is so poor."],
        'neutral': ["Ankle support is adequate.", "Could use a bit more rigidity."],
    },
    'weight': {
        'positive': ["Surprisingly lightweight for the features.", "Barely notice the weight.", "Ultralight without compromising performance."],
        'negative': ["Way too heavy for extended use.", "Feels like carrying bricks.", "The weight is a dealbreaker for long treks."],
        'neutral': ["Weight is about average.", "Not the lightest, not the heaviest."],
    },
    'price': {
        'positive': ["Excellent value for money.", "Worth every dollar.", "Premium quality at a fair price."],
        'negative': ["Massively overpriced for what you get.", "There are far better options at half the price.", "Not worth the premium markup."],
        'neutral': ["Price is on par with competitors.", "You get what you pay for."],
    },
    'grip': {
        'positive': ["Outstanding traction on wet rocks.", "The grip on varied terrain is incredible.", "Never once slipped on the trails."],
        'negative': ["Zero grip on wet surfaces.", "The soles are dangerously slippery.", "Lost traction on every downhill."],
        'neutral': ["Grip is decent on dry terrain.", "Okay traction for casual trails."],
    },
    'breathability': {
        'positive': ["Excellent airflow keeps feet cool.", "The ventilation is top-notch.", "No sweat buildup even in summer heat."],
        'negative': ["My feet were soaked in sweat.", "Zero breathability.", "Feels like wearing plastic bags."],
        'neutral': ["Breathability is acceptable.", "Some sweat buildup on hot days."],
    },
    'capacity': {
        'positive': ["Fits everything I need for a 3-day trip.", "Clever compartment design.", "More capacity than I expected."],
        'negative': ["Way too small for overnight hikes.", "Can barely fit essentials.", "The pockets are impractically small."],
        'neutral': ["Capacity is adequate for day trips.", "Fits the basics."],
    },
    'waterproofing': {
        'positive': ["Bone dry through a torrential downpour.", "Exceptional waterproofing.", "Kept everything dry in heavy rain."],
        'negative': ["Leaked within the first hour of rain.", "Waterproofing is nonexistent.", "Everything inside was soaked."],
        'neutral': ["Handles light rain okay.", "Some moisture seepage in heavy rain."],
    },
    'safety': {
        'positive': ["Feels incredibly secure on the wall.", "The safety features give total confidence.", "Passed every safety check with flying colors."],
        'negative': ["The buckle feels flimsy and unsafe.", "Doesn't inspire confidence at all.", "Safety mechanism jammed on me mid-climb."],
        'neutral': ["Safety features seem standard.", "Meets basic safety requirements."],
    },
    'reliability': {
        'positive': ["Lights up every single time, no issues.", "Completely reliable in all conditions.", "Never failed me once on the trail."],
        'negative': ["Failed to ignite in cold weather.", "Completely unreliable.", "Stopped working after the third trip."],
        'neutral': ["Works most of the time.", "Reliability is hit or miss."],
    },
    'portability': {
        'positive': ["Incredibly compact and packable.", "Weighs next to nothing.", "Fits easily in any pack."],
        'negative': ["Way too bulky for backpacking.", "Takes up too much space.", "Not portable at all despite marketing."],
        'neutral': ["Reasonably portable.", "A bit bulky but manageable."],
    },
    'fuel efficiency': {
        'positive': ["Uses remarkably little fuel.", "One canister lasted the entire trip.", "Incredibly efficient burn."],
        'negative': ["Burns through fuel absurdly fast.", "Terrible fuel economy.", "Went through two canisters in one day."],
        'neutral': ["Fuel consumption is average.", "Uses about as much fuel as expected."],
    },
    'ease of use': {
        'positive': ["Set up in under a minute.", "Intuitive design.", "Even beginners can use it right away."],
        'negative': ["Took 20 minutes to figure out.", "The instructions are useless.", "Overly complicated for what it does."],
        'neutral': ["Takes a bit of practice.", "Not the most intuitive."],
    },
}


def get_season(date):
    """Determine season from date."""
    month = date.month
    if month in (12, 1, 2):
        return 'Winter'
    elif month in (3, 4, 5):
        return 'Spring'
    elif month in (6, 7, 8):
        return 'Summer'
    else:
        return 'Fall'


def generate_review(product_name, product_info, review_date, campaign_id):
    """Generate a single realistic review with aspect-aware text."""
    season = get_season(review_date)

    # Sentiment distribution: 55% positive, 25% negative, 20% neutral
    sentiment_roll = random.random()
    if sentiment_roll < 0.55:
        sentiment_type = 'positive'
        rating = random.choice([4, 4, 5, 5, 5])
        templates = POSITIVE_TEMPLATES
    elif sentiment_roll < 0.80:
        sentiment_type = 'negative'
        rating = random.choice([1, 1, 2, 2, 3])
        templates = NEGATIVE_TEMPLATES
    else:
        sentiment_type = 'neutral'
        rating = random.choice([3, 3, 3, 4])
        templates = NEUTRAL_TEMPLATES

    # Pick a random aspect for this product
    aspect = random.choice(product_info['aspects'])
    detail_options = ASPECT_DETAILS.get(aspect, {}).get(sentiment_type, [""])
    if not detail_options:
        detail_options = ASPECT_DETAILS.get(aspect, {}).get('neutral', [""])
    detail = random.choice(detail_options) if detail_options else ""

    template = random.choice(templates)
    review_text = template.format(
        product=product_name,
        aspect=aspect,
        detail=detail,
        season=season.lower()
    )

    return {
        'review_id': f"REV-{fake.unique.random_int(min=10000, max=99999)}",
        'customer_name': fake.name() if random.random() > 0.08 else None,  # 8% null names
        'product_name': product_name,
        'product_category': product_info['category'],
        'review_text': review_text,
        'rating': rating,
        'review_date': review_date.strftime('%Y-%m-%d'),
        'source': random.choice(SOURCES),
        'campaign_id': campaign_id,
        'is_verified_purchase': 1 if random.random() > 0.15 else 0,
    }


def generate_campaigns():
    """Generate campaign data with specific CTR and conversion metrics."""
    campaigns = [
        # Pre-optimization campaigns (low conversion: ~5%)
        {
            'campaign_id': 'CAMP-001',
            'campaign_name': 'Winter Kickoff 2024',
            'product_category': 'Footwear',
            'start_date': '2024-10-01',
            'end_date': '2024-11-30',
            'impressions': 45000,
            'clicks': 3150,     # 7.0% CTR
            'conversions': 158, # 5.0% conversion
            'spend': 8500.00,
            'season': 'Fall',
        },
        {
            'campaign_id': 'CAMP-002',
            'campaign_name': 'Holiday Gear Sale',
            'product_category': 'Apparel',
            'start_date': '2024-12-01',
            'end_date': '2024-12-31',
            'impressions': 62000,
            'clicks': 5580,     # 9.0% CTR
            'conversions': 335, # 6.0% conversion
            'spend': 12000.00,
            'season': 'Winter',
        },
        {
            'campaign_id': 'CAMP-003',
            'campaign_name': 'Ski Season Blitz',
            'product_category': 'Footwear',
            'start_date': '2025-01-01',
            'end_date': '2025-02-28',
            'impressions': 85000,
            'clicks': 13090,    # 15.4% CTR  ← THE 15.4% CTR
            'conversions': 2422, # 18.5% conversion  ← THE 18.5% CONVERSION
            'spend': 18500.00,
            'season': 'Winter',
        },
        {
            'campaign_id': 'CAMP-004',
            'campaign_name': 'Spring Trail Ready',
            'product_category': 'Footwear',
            'start_date': '2025-03-01',
            'end_date': '2025-04-30',
            'impressions': 38000,
            'clicks': 4560,     # 12.0% CTR
            'conversions': 684, # 15.0% conversion
            'spend': 7200.00,
            'season': 'Spring',
        },
        {
            'campaign_id': 'CAMP-005',
            'campaign_name': 'Summer Adventure Push',
            'product_category': 'Equipment',
            'start_date': '2025-05-01',
            'end_date': '2025-07-31',
            'impressions': 52000,
            'clicks': 6760,     # 13.0% CTR
            'conversions': 1081, # 16.0% conversion
            'spend': 11000.00,
            'season': 'Summer',
        },
        {
            'campaign_id': 'CAMP-006',
            'campaign_name': 'Back-to-Trail Fall',
            'product_category': 'Accessories',
            'start_date': '2025-08-01',
            'end_date': '2025-09-30',
            'impressions': 41000,
            'clicks': 4920,     # 12.0% CTR
            'conversions': 738, # 15.0% conversion
            'spend': 8800.00,
            'season': 'Fall',
        },
        {
            'campaign_id': 'CAMP-007',
            'campaign_name': 'Peak Season Climbers',
            'product_category': 'Equipment',
            'start_date': '2025-06-01',
            'end_date': '2025-08-31',
            'impressions': 29000,
            'clicks': 3190,     # 11.0% CTR
            'conversions': 510, # 16.0% conversion
            'spend': 6500.00,
            'season': 'Summer',
        },
        {
            'campaign_id': 'CAMP-008',
            'campaign_name': 'Winter Warmth Revival',
            'product_category': 'Apparel',
            'start_date': '2025-10-01',
            'end_date': '2025-12-31',
            'impressions': 55000,
            'clicks': 7700,     # 14.0% CTR
            'conversions': 1309, # 17.0% conversion
            'spend': 14000.00,
            'season': 'Winter',
        },
    ]
    return campaigns


def generate_reviews(campaigns):
    """Generate 650+ reviews distributed across seasons and products."""
    reviews = []
    start_date = datetime(2024, 10, 1)
    end_date = datetime(2025, 12, 31)

    campaign_date_map = {}
    for c in campaigns:
        s = datetime.strptime(c['start_date'], '%Y-%m-%d')
        e = datetime.strptime(c['end_date'], '%Y-%m-%d')
        campaign_date_map[c['campaign_id']] = (s, e, c['product_category'])

    target_count = 670  # Aim for 670 to ensure 650+ after dedup
    generated = 0

    current = start_date
    while current <= end_date and generated < target_count:
        season = get_season(current)

        for product_name, info in PRODUCTS.items():
            weight = info['seasonal_weight'].get(season, 1.0)

            # Determine how many reviews this product gets today
            daily_chance = weight * 0.12
            num_reviews = 0
            if random.random() < daily_chance:
                num_reviews = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]

            for _ in range(num_reviews):
                if generated >= target_count:
                    break

                # Find matching campaign
                campaign_id = None
                for cid, (cs, ce, ccat) in campaign_date_map.items():
                    if cs <= current <= ce:
                        if ccat == info['category'] or random.random() < 0.3:
                            campaign_id = cid
                            break

                review_date = current + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                review = generate_review(product_name, info, review_date, campaign_id)
                reviews.append(review)
                generated += 1

        current += timedelta(days=1)

    # Add ~30 duplicate review_ids (for ETL dedup demo)
    duplicates = random.sample(reviews, min(30, len(reviews)))
    for dup in duplicates:
        dup_copy = dup.copy()
        dup_copy['id'] = None  # new auto-increment id
        reviews.append(dup_copy)

    random.shuffle(reviews)
    return reviews


def populate_database():
    """Create database and populate with synthetic data."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Remove existing DB for fresh start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Execute schema DDL
    sql_dir = os.path.join(os.path.dirname(__file__), 'sql')
    with open(os.path.join(sql_dir, '01_create_tables.sql'), 'r') as f:
        cursor.executescript(f.read())

    # Insert campaigns
    campaigns = generate_campaigns()
    for c in campaigns:
        cursor.execute("""
            INSERT INTO campaigns (campaign_id, campaign_name, product_category,
                start_date, end_date, impressions, clicks, conversions, spend, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (c['campaign_id'], c['campaign_name'], c['product_category'],
              c['start_date'], c['end_date'], c['impressions'], c['clicks'],
              c['conversions'], c['spend'], c['season']))

    # Insert reviews
    reviews = generate_reviews(campaigns)
    for r in reviews:
        cursor.execute("""
            INSERT INTO raw_reviews (review_id, customer_name, product_name,
                product_category, review_text, rating, review_date, source,
                campaign_id, is_verified_purchase)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (r['review_id'], r['customer_name'], r['product_name'],
              r['product_category'], r['review_text'], r['rating'],
              r['review_date'], r['source'], r['campaign_id'],
              r['is_verified_purchase']))

    conn.commit()

    # Summary stats
    cursor.execute("SELECT COUNT(*) FROM raw_reviews")
    total_reviews = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT review_id) FROM raw_reviews")
    unique_reviews = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM campaigns")
    total_campaigns = cursor.fetchone()[0]

    print(f"✓ Generated {total_reviews} raw reviews ({unique_reviews} unique, {total_reviews - unique_reviews} duplicates)")
    print(f"✓ Generated {total_campaigns} campaigns")
    print(f"✓ Database saved to: {DB_PATH}")

    conn.close()
    return total_reviews, unique_reviews


if __name__ == '__main__':
    print("=" * 60)
    print("Campaign Sentiment & Customer Voice Analysis")
    print("Synthetic Data Generator")
    print("=" * 60)
    populate_database()
