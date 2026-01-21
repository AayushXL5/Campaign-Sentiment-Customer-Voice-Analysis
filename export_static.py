"""Export dashboard data as static JSON for Vercel/static hosting."""
import json, sqlite3, os

DB = os.path.join(os.path.dirname(__file__), 'data', 'campaign_voice.db')

def get_season(date_str):
    m = int(date_str.split('-')[1]) if date_str and '-' in date_str else 0
    if m in (12,1,2): return 'Winter'
    elif m in (3,4,5): return 'Spring'
    elif m in (6,7,8): return 'Summer'
    else: return 'Fall'

def export():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    data = {}

    reviews = conn.execute('SELECT * FROM cleaned_reviews ORDER BY review_date DESC').fetchall()
    data['all_reviews'] = []
    for r in reviews:
        d = dict(r)
        d['season'] = get_season(d.get('review_date', ''))
        data['all_reviews'].append(d)

    total = len(data['all_reviews'])
    avg_s = sum(r['sentiment_compound'] or 0 for r in data['all_reviews']) / max(total, 1)
    best_ctr = conn.execute("SELECT ROUND(100.0*clicks/NULLIF(impressions,0),1) as ctr FROM campaigns ORDER BY ctr DESC LIMIT 1").fetchone()
    best_conv = conn.execute("SELECT ROUND(100.0*conversions/NULLIF(clicks,0),1) as conv FROM campaigns ORDER BY conv DESC LIMIT 1").fetchone()
    data['kpis'] = {
        'total_reviews': total,
        'avg_sentiment': round(avg_s, 4),
        'best_ctr': best_ctr[0] if best_ctr else 0,
        'best_conversion': best_conv[0] if best_conv else 0,
    }

    data['campaign_performance'] = [dict(c) for c in conn.execute(
        "SELECT campaign_name,season,impressions,clicks,ROUND(100.0*clicks/NULLIF(impressions,0),1) as ctr,conversions,ROUND(100.0*conversions/NULLIF(clicks,0),1) as conversion_rate,spend FROM campaigns ORDER BY start_date"
    ).fetchall()]

    data['themes'] = [dict(t) for t in conn.execute("SELECT * FROM review_themes ORDER BY mention_count DESC LIMIT 50").fetchall()]
    data['aspect_sentiment'] = [dict(a) for a in conn.execute("SELECT * FROM aspect_sentiment ORDER BY product_name,aspect").fetchall()]
    data['pain_points'] = [dict(p) for p in conn.execute("SELECT * FROM pain_points ORDER BY frequency DESC").fetchall()]
    data['segments'] = [dict(s) for s in conn.execute(
        "SELECT * FROM customer_segments ORDER BY CASE segment_name WHEN 'Promoter' THEN 1 WHEN 'Passive' THEN 2 ELSE 3 END"
    ).fetchall()]

    conn.close()

    os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'data'), exist_ok=True)
    out_path = os.path.join(os.path.dirname(__file__), 'static', 'data', 'dashboard-data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Exported {total} reviews to {out_path}")

if __name__ == '__main__':
    export()
