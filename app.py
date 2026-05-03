"""
Flask App — Dashboard + API + CSV Export
"""
import sqlite3, os, io, csv, json, zipfile
from flask import Flask, render_template, jsonify, Response, send_file

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), 'data', 'campaign_voice.db')

def get_db():
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row; return conn

def get_season(date_str):
    m = int(date_str.split('-')[1]) if date_str and '-' in date_str else 0
    if m in (12,1,2): return 'Winter'
    elif m in (3,4,5): return 'Spring'
    elif m in (6,7,8): return 'Summer'
    else: return 'Fall'

@app.route('/')
def dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM cleaned_reviews").fetchone()[0]
    conn.close()
    return render_template('dashboard.html', total_reviews=total)

@app.route('/api/dashboard-data')
def api_data():
    conn = get_db()
    data = {}

    # All reviews (full dataset for client-side filtering)
    reviews = conn.execute("""
        SELECT review_id, customer_name, product_name, product_category,
               review_text, rating, review_date, source, campaign_id,
               sentiment_compound, sentiment_pos, sentiment_neg, sentiment_neu,
               sentiment_label
        FROM cleaned_reviews ORDER BY review_date DESC
    """).fetchall()

    data['all_reviews'] = []
    for r in reviews:
        d = dict(r)
        d['season'] = get_season(d.get('review_date', ''))
        data['all_reviews'].append(d)

    # KPIs
    total = len(data['all_reviews'])
    avg_s = sum(r['sentiment_compound'] or 0 for r in data['all_reviews']) / max(total, 1)
    best_ctr = conn.execute("SELECT ROUND(100.0*clicks/NULLIF(impressions,0),1) as ctr FROM campaigns ORDER BY ctr DESC LIMIT 1").fetchone()
    best_conv = conn.execute("SELECT ROUND(100.0*conversions/NULLIF(clicks,0),1) as conv FROM campaigns ORDER BY conv DESC LIMIT 1").fetchone()
    data['kpis'] = {'total_reviews': total, 'avg_sentiment': round(avg_s, 4), 'best_ctr': best_ctr[0] if best_ctr else 0, 'best_conversion': best_conv[0] if best_conv else 0}

    # Campaigns
    data['campaign_performance'] = [dict(c) for c in conn.execute("""
        SELECT campaign_name, season, impressions, clicks,
               ROUND(100.0*clicks/NULLIF(impressions,0),1) as ctr,
               conversions, ROUND(100.0*conversions/NULLIF(clicks,0),1) as conversion_rate, spend
        FROM campaigns ORDER BY start_date
    """).fetchall()]

    # Themes
    data['themes'] = [dict(t) for t in conn.execute("SELECT * FROM review_themes ORDER BY mention_count DESC LIMIT 50").fetchall()]

    # Aspect sentiment
    data['aspect_sentiment'] = [dict(a) for a in conn.execute("SELECT * FROM aspect_sentiment ORDER BY product_name, aspect").fetchall()]

    # Pain points
    data['pain_points'] = [dict(p) for p in conn.execute("SELECT * FROM pain_points ORDER BY frequency DESC").fetchall()]

    # Segments
    data['segments'] = [dict(s) for s in conn.execute("""
        SELECT * FROM customer_segments ORDER BY CASE segment_name
        WHEN 'Promoter' THEN 1 WHEN 'Passive' THEN 2 ELSE 3 END
    """).fetchall()]

    conn.close()
    return jsonify(data)

# ── CSV Exports ──────────────────────────────────────────────────
@app.route('/export/reviews')
def export_reviews():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM cleaned_reviews ORDER BY review_date DESC")
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(cols)
    for r in rows: w.writerow(list(r))
    return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="cleaned_reviews.csv"'})

@app.route('/export/campaigns')
def export_campaigns():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM campaigns ORDER BY start_date")
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(cols)
    for r in rows: w.writerow(list(r))
    return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="campaigns.csv"'})

@app.route('/export/voice')
def export_voice():
    conn = get_db()
    tables = {'pain_points': 'pain_points', 'aspect_sentiment': 'aspect_sentiment',
              'review_themes': 'review_themes', 'customer_segments': 'customer_segments',
              'keyword_frequency': 'keyword_frequency'}
    si = io.StringIO()
    for label, table in tables.items():
        cursor = conn.execute(f"SELECT * FROM {table}")
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        si.write(f"\n--- {label.upper()} ---\n")
        w = csv.writer(si)
        w.writerow(cols)
        for r in rows: w.writerow(list(r))
    conn.close()
    return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="voice_analysis.csv"'})

@app.route('/export/all')
def export_all():
    conn = get_db()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for table in ['cleaned_reviews', 'campaigns', 'pain_points', 'aspect_sentiment',
                       'review_themes', 'customer_segments', 'keyword_frequency', 'campaign_metrics']:
            try:
                cursor = conn.execute(f"SELECT * FROM {table}")
                cols = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
                si = io.StringIO()
                w = csv.writer(si)
                w.writerow(cols)
                for r in rows: w.writerow(list(r))
                zf.writestr(f"{table}.csv", si.getvalue())
            except: pass
    conn.close()
    buf.seek(0)
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name='campaign_voice_data.zip')

if __name__ == '__main__':
    print("Dashboard: http://localhost:5000")
    app.run(debug=True, port=5000)
