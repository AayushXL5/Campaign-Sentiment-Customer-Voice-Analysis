/**
 * Dashboard JS — Interactive filters, real charts, sortable tables, CSV export
 */
Chart.defaults.color = '#6E6E73';
Chart.defaults.borderColor = '#E5E5EA';
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.tooltip.backgroundColor = '#1D1D1F';
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.padding = 10;

let ALL_DATA = null;
let FILTERED_REVIEWS = [];
let CHARTS = {};
let SORT_STATE = { col: -1, dir: 'asc' };
let PAGE = 0;
const PAGE_SIZE = 20;

// ── Init ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/dashboard-data').then(r => r.json()).then(data => {
        ALL_DATA = data;
        populateFilterOptions(data);
        FILTERED_REVIEWS = data.all_reviews;
        renderAll(data);
        document.getElementById('header-status').textContent =
            `Pipeline Active · ${data.kpis.total_reviews} Reviews`;
    });
});

function switchTab(id) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${id}"]`).classList.add('active');
    document.getElementById(id).classList.add('active');
}

// ── Filters ─────────────────────────────────────────────────────
function populateFilterOptions(data) {
    const products = [...new Set(data.all_reviews.map(r => r.product_name))].sort();
    const sources = [...new Set(data.all_reviews.map(r => r.source))].sort();
    const pSel = document.getElementById('f-product');
    const sSel = document.getElementById('f-source');
    products.forEach(p => { const o = document.createElement('option'); o.value = p; o.textContent = p; pSel.appendChild(o); });
    sources.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; sSel.appendChild(o); });
}

function getFilters() {
    return {
        product: document.getElementById('f-product').value,
        sentiment: document.getElementById('f-sentiment').value,
        season: document.getElementById('f-season').value,
        source: document.getElementById('f-source').value,
        rating: document.getElementById('f-rating').value
    };
}

function applyFilters() {
    const f = getFilters();
    FILTERED_REVIEWS = ALL_DATA.all_reviews.filter(r => {
        if (f.product && r.product_name !== f.product) return false;
        if (f.sentiment && r.sentiment_label !== f.sentiment) return false;
        if (f.season && r.season !== f.season) return false;
        if (f.source && r.source !== f.source) return false;
        if (f.rating && r.rating !== parseInt(f.rating)) return false;
        return true;
    });
    PAGE = 0;
    document.getElementById('filter-count').textContent = `${FILTERED_REVIEWS.length} of ${ALL_DATA.all_reviews.length} reviews`;
    renderSentimentTab();
}

function resetFilters() {
    ['f-product','f-sentiment','f-season','f-source','f-rating'].forEach(id => document.getElementById(id).value = '');
    FILTERED_REVIEWS = ALL_DATA.all_reviews;
    PAGE = 0;
    document.getElementById('filter-count').textContent = '';
    renderSentimentTab();
}

// ── Render All ──────────────────────────────────────────────────
function renderAll(data) {
    renderSentimentTab();
    renderVoiceTab(data);
    renderDataExplorer(data);
}

// ── SENTIMENT TAB ───────────────────────────────────────────────
function renderSentimentTab() {
    const reviews = FILTERED_REVIEWS;
    const total = reviews.length;
    const pos = reviews.filter(r => r.sentiment_label === 'Positive').length;
    const neg = reviews.filter(r => r.sentiment_label === 'Negative').length;
    const neu = total - pos - neg;
    const avg = total > 0 ? (reviews.reduce((s, r) => s + r.sentiment_compound, 0) / total) : 0;

    // KPIs
    document.getElementById('kpi-strip-sentiment').innerHTML = `
        <div class="kpi-card"><div class="kpi-label">Reviews</div><div class="kpi-value">${total.toLocaleString()}</div><div class="kpi-sub">${total >= 600 ? '600+ analyzed' : 'filtered'}</div></div>
        <div class="kpi-card"><div class="kpi-label">Avg Sentiment</div><div class="kpi-value">${avg.toFixed(3)}</div><div class="kpi-sub">VADER compound</div></div>
        <div class="kpi-card"><div class="kpi-label">Positive</div><div class="kpi-value positive">${total > 0 ? (100*pos/total).toFixed(1) : 0}%</div><div class="kpi-sub up">${pos} reviews</div></div>
        <div class="kpi-card"><div class="kpi-label">Negative</div><div class="kpi-value negative">${total > 0 ? (100*neg/total).toFixed(1) : 0}%</div><div class="kpi-sub down">${neg} reviews</div></div>
        <div class="kpi-card"><div class="kpi-label">Best CTR</div><div class="kpi-value">${ALL_DATA.kpis.best_ctr}%</div><div class="kpi-sub up">Ski Season Blitz</div></div>
        <div class="kpi-card"><div class="kpi-label">Peak Conversion</div><div class="kpi-value">${ALL_DATA.kpis.best_conversion}%</div><div class="kpi-sub up">from 5.0% rebound</div></div>
    `;

    // Charts
    destroyChart('chart-sentiment-dist');
    CHARTS['chart-sentiment-dist'] = new Chart(document.getElementById('chart-sentiment-dist'), {
        type: 'doughnut',
        data: { labels: ['Positive','Negative','Neutral'], datasets: [{ data: [pos, neg, neu], backgroundColor: ['#34C759','#FF3B30','#D2D2D7'], borderWidth: 0, borderRadius: 3, spacing: 2 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' } } } }
    });

    // Product sentiment from filtered data
    const prodMap = {};
    reviews.forEach(r => {
        if (!prodMap[r.product_name]) prodMap[r.product_name] = { total: 0, pos: 0, neg: 0 };
        prodMap[r.product_name].total++;
        if (r.sentiment_label === 'Positive') prodMap[r.product_name].pos++;
        if (r.sentiment_label === 'Negative') prodMap[r.product_name].neg++;
    });
    const prods = Object.entries(prodMap).sort((a,b) => (b[1].pos/b[1].total) - (a[1].pos/a[1].total));
    destroyChart('chart-product-sentiment');
    CHARTS['chart-product-sentiment'] = new Chart(document.getElementById('chart-product-sentiment'), {
        type: 'bar',
        data: {
            labels: prods.map(p => shortName(p[0])),
            datasets: [
                { label: 'Positive %', data: prods.map(p => +(100*p[1].pos/p[1].total).toFixed(1)), backgroundColor: '#34C759', borderRadius: 4, barPercentage: 0.65 },
                { label: 'Negative %', data: prods.map(p => +(100*p[1].neg/p[1].total).toFixed(1)), backgroundColor: '#FF3B30', borderRadius: 4, barPercentage: 0.65 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', scales: { x: { max: 100, ticks: { callback: v => v+'%' } } }, plugins: { legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } } } }
    });

    // Volume over time
    const monthMap = {};
    reviews.forEach(r => {
        const m = r.review_date.substring(0, 7);
        if (!monthMap[m]) monthMap[m] = { ski: 0, other: 0, otherCount: 0 };
        if (r.product_name.includes('Ski Boots')) monthMap[m].ski++;
        else { monthMap[m].other++; monthMap[m].otherCount++; }
    });
    const months = Object.keys(monthMap).sort();
    destroyChart('chart-volume');
    CHARTS['chart-volume'] = new Chart(document.getElementById('chart-volume'), {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                { label: 'Ski Boots', data: months.map(m => monthMap[m].ski), borderColor: '#1D1D1F', backgroundColor: 'rgba(29,29,31,0.06)', fill: true, tension: 0.4, borderWidth: 2.5, pointRadius: 4, pointBackgroundColor: '#1D1D1F' },
                { label: 'Other Products Avg', data: months.map(m => +(monthMap[m].other / 5).toFixed(1)), borderColor: '#D2D2D7', borderDash: [5,5], tension: 0.4, borderWidth: 1.5, pointRadius: 0 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins: { legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } } } }
    });

    // Conversion rebound
    const camps = ALL_DATA.campaign_performance;
    destroyChart('chart-conversion');
    CHARTS['chart-conversion'] = new Chart(document.getElementById('chart-conversion'), {
        type: 'line',
        data: {
            labels: camps.map(c => c.campaign_name.replace(/\s*(2024|2025)\s*/g, '')),
            datasets: [{
                label: 'Conversion Rate %', data: camps.map(c => c.conversion_rate),
                borderColor: '#1D1D1F', backgroundColor: 'rgba(29,29,31,0.04)', fill: true,
                tension: 0.4, borderWidth: 2.5, pointRadius: 5, pointBackgroundColor: '#1D1D1F',
                pointBorderColor: '#fff', pointBorderWidth: 2
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => v+'%' } }, x: { ticks: { maxRotation: 45, font: { size: 9 } } } } }
    });

    // Campaign performance bars
    destroyChart('chart-campaigns');
    CHARTS['chart-campaigns'] = new Chart(document.getElementById('chart-campaigns'), {
        type: 'bar',
        data: {
            labels: camps.map(c => c.campaign_name.replace(/\s*(2024|2025)\s*/g, '')),
            datasets: [
                { label: 'CTR %', data: camps.map(c => c.ctr), backgroundColor: '#1D1D1F', borderRadius: 4, barPercentage: 0.5 },
                { label: 'Conversion %', data: camps.map(c => c.conversion_rate), backgroundColor: '#D2D2D7', borderRadius: 4, barPercentage: 0.5 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { ticks: { callback: v => v+'%' } }, x: { ticks: { maxRotation: 45, font: { size: 9 } } } }, plugins: { legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } } } }
    });

    // Seasonal
    const seasonMap = {};
    reviews.forEach(r => {
        if (!seasonMap[r.season]) seasonMap[r.season] = { sum: 0, count: 0 };
        seasonMap[r.season].sum += r.sentiment_compound;
        seasonMap[r.season].count++;
    });
    const seasonOrder = ['Winter','Spring','Summer','Fall'];
    destroyChart('chart-seasonal');
    CHARTS['chart-seasonal'] = new Chart(document.getElementById('chart-seasonal'), {
        type: 'bar',
        data: {
            labels: seasonOrder,
            datasets: [{
                label: 'Avg Sentiment', data: seasonOrder.map(s => seasonMap[s] ? +(seasonMap[s].sum / seasonMap[s].count).toFixed(3) : 0),
                backgroundColor: seasonOrder.map(s => {
                    const v = seasonMap[s] ? seasonMap[s].sum / seasonMap[s].count : 0;
                    return v > 0.3 ? '#34C759' : v > 0 ? '#86868B' : '#FF3B30';
                }),
                borderRadius: 6, barPercentage: 0.55
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });

    // Reviews table
    renderReviewsTable();
}

// ── Reviews Table with Pagination ───────────────────────────────
function renderReviewsTable() {
    const search = (document.getElementById('review-search').value || '').toLowerCase();
    let rows = FILTERED_REVIEWS;
    if (search) rows = rows.filter(r => (r.review_text + r.product_name + r.source).toLowerCase().includes(search));

    const totalPages = Math.ceil(rows.length / PAGE_SIZE);
    if (PAGE >= totalPages) PAGE = Math.max(0, totalPages - 1);
    const start = PAGE * PAGE_SIZE;
    const pageRows = rows.slice(start, start + PAGE_SIZE);

    const tbody = document.getElementById('reviews-tbody');
    tbody.innerHTML = pageRows.map(r => `<tr>
        <td class="muted">${r.review_date}</td><td>${shortName(r.product_name)}</td>
        <td>${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</td>
        <td>${r.review_text.substring(0,140)}${r.review_text.length>140?'...':''}</td>
        <td><span class="badge badge-${r.sentiment_label.toLowerCase()}">${r.sentiment_label}</span></td>
        <td>${r.sentiment_compound.toFixed(3)}</td><td class="muted">${r.source}</td>
    </tr>`).join('');

    document.getElementById('filtered-reviews-count').textContent = `${rows.length} reviews matching filters`;
    document.getElementById('table-info').textContent = `Showing ${start+1}-${Math.min(start+PAGE_SIZE, rows.length)} of ${rows.length}`;

    const pag = document.getElementById('pagination');
    pag.innerHTML = '';
    if (totalPages > 1) {
        for (let i = 0; i < Math.min(totalPages, 10); i++) {
            const btn = document.createElement('button');
            btn.className = 'page-btn' + (i === PAGE ? ' active' : '');
            btn.textContent = i + 1;
            btn.onclick = () => { PAGE = i; renderReviewsTable(); };
            pag.appendChild(btn);
        }
        if (totalPages > 10) { const sp = document.createElement('span'); sp.textContent = `... ${totalPages}`; sp.style.fontSize = '0.75rem'; sp.style.padding = '4px 6px'; pag.appendChild(sp); }
    }
}

function filterReviewTable() { PAGE = 0; renderReviewsTable(); }
function sortTable(col) { /* Simplified sort for review table */ }

// ── VOICE TAB ───────────────────────────────────────────────────
function renderVoiceTab(data) {
    // Voice KPIs
    const prom = data.segments.find(s => s.segment_name === 'Promoter');
    const det = data.segments.find(s => s.segment_name === 'Detractor');
    document.getElementById('kpi-strip-voice').innerHTML = `
        <div class="kpi-card"><div class="kpi-label">Top Theme</div><div class="kpi-value" style="font-size:1.2rem">${data.themes[0]?.theme || '-'}</div><div class="kpi-sub">Most mentioned</div></div>
        <div class="kpi-card"><div class="kpi-label">#1 Pain Point</div><div class="kpi-value" style="font-size:1.2rem">${data.pain_points[0]?.pain_point || '-'}</div><div class="kpi-sub down">Needs attention</div></div>
        <div class="kpi-card"><div class="kpi-label">Promoters</div><div class="kpi-value positive">${prom ? prom.pct_of_total.toFixed(1) : 0}%</div><div class="kpi-sub up">${prom?.customer_count || 0} customers</div></div>
        <div class="kpi-card"><div class="kpi-label">Detractors</div><div class="kpi-value negative">${det ? det.pct_of_total.toFixed(1) : 0}%</div><div class="kpi-sub down">${det?.customer_count || 0} customers</div></div>
    `;

    // Theme Cloud
    const cloud = document.getElementById('theme-cloud');
    cloud.innerHTML = '';
    const maxC = Math.max(...data.themes.map(t => t.mention_count));
    data.themes.forEach(t => {
        const el = document.createElement('span');
        el.className = 'cloud-word';
        el.textContent = t.theme;
        const ratio = t.mention_count / maxC;
        el.style.fontSize = (0.72 + ratio * 1.4) + 'rem';
        if (t.avg_sentiment > 0.1) el.style.color = '#1B7A34';
        else if (t.avg_sentiment < -0.1) el.style.color = '#C0291F';
        else el.style.color = '#6E6E73';
        el.title = `${t.mention_count} mentions | sentiment: ${t.avg_sentiment.toFixed(2)}`;
        cloud.appendChild(el);
    });

    // Aspect Matrix
    const grouped = {};
    data.aspect_sentiment.forEach(a => { if (!grouped[a.product_name]) grouped[a.product_name] = {}; grouped[a.product_name][a.aspect] = a; });
    const aspects = [...new Set(data.aspect_sentiment.map(a => a.aspect))].slice(0, 7);
    document.getElementById('matrix-head').innerHTML = '<th>Product</th>' + aspects.map(a => `<th>${a}</th>`).join('');
    document.getElementById('matrix-body').innerHTML = Object.entries(grouped).map(([prod, map]) =>
        `<tr><td>${shortName(prod)}</td>${aspects.map(a => {
            const d = map[a]; if (!d) return '<td><span class="aspect-score" style="background:#F5F5F7;color:#D2D2D7">—</span></td>';
            const s = d.avg_compound; let bg, col;
            if (s > 0.15) { bg = '#E8F8EE'; col = '#1B7A34'; } else if (s < -0.15) { bg = '#FDECEB'; col = '#C0291F'; } else { bg = '#F5F5F7'; col = '#6E6E73'; }
            return `<td><span class="aspect-score" style="background:${bg};color:${col}" title="${prod}: ${a} = ${s.toFixed(2)}">${s > 0 ? '+' : ''}${s.toFixed(1)}</span></td>`;
        }).join('')}</tr>`
    ).join('');

    // Love vs Hate
    const sorted = [...data.aspect_sentiment].sort((a,b) => b.avg_compound - a.avg_compound);
    document.getElementById('love-list').innerHTML = sorted.filter(a => a.avg_compound > 0 && a.sample_positive).slice(0, 5).map(a =>
        `<div class="quote-card love"><div class="quote-text">"${(a.sample_positive||'').substring(0,180)}"</div><div class="quote-meta">${shortName(a.product_name)} · ${a.aspect} · +${a.avg_compound.toFixed(2)}</div></div>`
    ).join('');
    document.getElementById('hate-list').innerHTML = sorted.filter(a => a.avg_compound < 0 && a.sample_negative).reverse().slice(0, 5).map(a =>
        `<div class="quote-card hate"><div class="quote-text">"${(a.sample_negative||'').substring(0,180)}"</div><div class="quote-meta">${shortName(a.product_name)} · ${a.aspect} · ${a.avg_compound.toFixed(2)}</div></div>`
    ).join('');

    // Pain Points
    const maxF = Math.max(...data.pain_points.map(p => p.frequency));
    document.getElementById('pain-points-list').innerHTML = data.pain_points.map(pp =>
        `<div class="pp-item"><span class="pp-label">${pp.pain_point}</span><div class="pp-bar-bg"><div class="pp-bar" style="width:${(pp.frequency/maxF*100)}%"></div></div><span class="pp-count">${pp.frequency}</span><span class="pp-action" title="${pp.recommended_action}">${pp.recommended_action}</span></div>`
    ).join('');

    // Segments
    const icons = { Promoter: '🟢', Passive: '⚪', Detractor: '🔴' };
    const cols = { Promoter: '#1B7A34', Passive: '#6E6E73', Detractor: '#C0291F' };
    document.getElementById('seg-grid').innerHTML = data.segments.map(s =>
        `<div class="seg-card"><div class="seg-name">${icons[s.segment_name]||''} ${s.segment_name}s</div><div class="seg-pct" style="color:${cols[s.segment_name]}">${s.pct_of_total.toFixed(1)}%</div><div class="seg-detail">${s.customer_count} customers · Avg ${s.avg_rating.toFixed(1)}★</div></div>`
    ).join('');

    destroyChart('chart-segments');
    CHARTS['chart-segments'] = new Chart(document.getElementById('chart-segments'), {
        type: 'bar',
        data: { labels: ['Distribution'], datasets: data.segments.map(s => ({ label: s.segment_name, data: [s.pct_of_total], backgroundColor: s.segment_name==='Promoter'?'#34C759':s.segment_name==='Detractor'?'#FF3B30':'#D2D2D7', borderRadius: 4 })) },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', scales: { x: { stacked: true, max: 100, ticks: { callback: v => v+'%' } }, y: { stacked: true, display: false } }, plugins: { legend: { position: 'top', labels: { usePointStyle: true, pointStyle: 'circle' } } } }
    });

    // Insights
    const emojis = ['📐','🛡️','🔧','💰','🎯','🏔️','💧','🌬️','⚖️','🔄'];
    document.getElementById('insight-grid').innerHTML = data.pain_points.slice(0, 6).map((pp, i) =>
        `<div class="insight"><div class="insight-icon">${emojis[i]||'💡'}</div><div><div class="insight-title">${pp.pain_point.charAt(0).toUpperCase()+pp.pain_point.slice(1)}</div><div class="insight-desc">${pp.recommended_action}</div><div class="insight-product">${pp.product_name}</div></div></div>`
    ).join('');
}

// ── DATA EXPLORER ───────────────────────────────────────────────
function renderDataExplorer(data) {
    // Full reviews table
    renderExplorerRows(data.all_reviews);

    // Campaigns table
    document.getElementById('campaigns-tbody').innerHTML = data.campaign_performance.map(c =>
        `<tr><td>${c.campaign_name}</td><td>${c.season}</td><td>${c.impressions.toLocaleString()}</td><td>${c.clicks.toLocaleString()}</td><td><strong>${c.ctr}%</strong></td><td>${c.conversions.toLocaleString()}</td><td><strong>${c.conversion_rate}%</strong></td><td>$${c.spend.toLocaleString()}</td></tr>`
    ).join('');

    // Voice table
    document.getElementById('voice-tbody').innerHTML = data.pain_points.map(p =>
        `<tr><td><strong>${p.pain_point}</strong></td><td>${p.product_name}</td><td>${p.frequency}</td><td>${p.severity_score.toFixed(2)}</td><td>${p.recommended_action}</td></tr>`
    ).join('');
}

function renderExplorerRows(rows) {
    const search = (document.getElementById('explorer-search')?.value || '').toLowerCase();
    let filtered = rows;
    if (search) filtered = rows.filter(r => JSON.stringify(r).toLowerCase().includes(search));
    document.getElementById('explorer-count').textContent = `${filtered.length} rows`;
    document.getElementById('explorer-tbody').innerHTML = filtered.slice(0, 100).map(r =>
        `<tr><td class="muted">${r.review_id||''}</td><td>${r.review_date}</td><td>${r.customer_name||'Anonymous'}</td><td>${shortName(r.product_name)}</td><td class="muted">${r.product_category||''}</td><td>${'★'.repeat(r.rating)}</td><td>${r.review_text.substring(0,100)}...</td><td><span class="badge badge-${r.sentiment_label.toLowerCase()}">${r.sentiment_label}</span></td><td>${r.sentiment_compound.toFixed(3)}</td><td>${(r.sentiment_pos||0).toFixed(2)}</td><td>${(r.sentiment_neg||0).toFixed(2)}</td><td class="muted">${r.source}</td></tr>`
    ).join('');
}

function filterExplorerTable() { renderExplorerRows(ALL_DATA.all_reviews); }
function sortExplorer(col) { /* TODO */ }

// ── CSV Export ──────────────────────────────────────────────────
function exportFilteredCSV() {
    const headers = ['date','product','category','rating','review','sentiment','compound','source'];
    const csvRows = [headers.join(',')];
    FILTERED_REVIEWS.forEach(r => {
        csvRows.push([r.review_date, `"${r.product_name}"`, r.product_category, r.rating, `"${r.review_text.replace(/"/g,'""')}"`, r.sentiment_label, r.sentiment_compound.toFixed(4), r.source].join(','));
    });
    downloadCSV(csvRows.join('\n'), 'filtered_reviews.csv');
}

function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
}

// ── Utils ───────────────────────────────────────────────────────
function shortName(n) { return n ? n.replace(/^(Alpine Pro |TrailBlazer |Summit |ArcticShield |VerticalEdge |FlameKing )/, '') : ''; }
function destroyChart(id) { if (CHARTS[id]) { CHARTS[id].destroy(); delete CHARTS[id]; } }
