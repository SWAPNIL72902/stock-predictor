/* 
  Stable Frontend Logic for Terminal.AI
  Handles Async flow, UI Syncing, and Error Recovery.
*/

let chart = null;

async function runPrediction() {
    const input = document.getElementById('ticker-input');
    const ticker = input.value.trim().toUpperCase();
    if (!input || !ticker) return;

    const btn = document.getElementById('predict-btn');
    const loader = document.getElementById('loader');
    const results = document.getElementById('results-area');
    const btnText = document.getElementById('btn-text');
    const errorBox = document.getElementById('error-box');

    // 1. Enter Loading State
    btn.disabled = true;
    btnText.textContent = 'Analyzing...';
    errorBox.classList.add('hidden');
    results.classList.add('hidden');
    loader.classList.remove('hidden');

    try {
        // 2. Parallel Fetch Phase
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };

        const [predRes, chartRes] = await Promise.all([
            fetch(`/predict?ticker=${ticker}`, { method: 'POST', headers }),
            fetch(`/stock-data?ticker=${ticker}`)
        ]);

        if (predRes.status === 401) { window.location.href = '/'; return; }
        
        const predData = await predRes.json();
        const chartData = await chartRes.json();

        if (!predRes.ok) throw new Error(predData.detail || 'Inference Failed');

        // 3. Update Visuals Phase
        updatePredictionUI(predData);
        updateChartUI(chartData);

        // 4. Reveal Phase
        loader.classList.add('hidden');
        results.classList.remove('hidden');

    } catch (err) {
        console.error(err);
        loader.classList.add('hidden');
        errorBox.textContent = err.message || 'Node Error: Data Stream Interrupted';
        errorBox.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Run Neural Forecast';
    }
}

function updatePredictionUI(data) {
    document.getElementById('active-id').textContent = data.ticker;
    const predEl = document.getElementById('prediction-badge');
    const bar = document.getElementById('conf-bar');
    const pct = document.getElementById('conf-pct');

    predEl.textContent = data.prediction;
    predEl.className = `prediction-val fade-in ${data.prediction === 'UP' ? 'up-color' : 'down-color'}`;
    
    // Smooth meter logic
    const score = (data.confidence * 100).toFixed(1);
    pct.textContent = `${score}%`;
    bar.style.width = `${score}%`;
    bar.style.backgroundColor = data.prediction === 'UP' ? '#00ff88' : '#ef4444';

    // News
    const newsArea = document.getElementById('news-list');
    newsArea.innerHTML = '';
    if (data.news && data.news.length > 0) {
        data.news.forEach(n => {
            const item = document.createElement('div');
            item.className = 'news-item fade-in';
            const badgeClass = n.sentiment_label === 'Positive' ? 'pos-badge' : n.sentiment_label === 'Negative' ? 'neg-badge' : 'neu-badge';
            item.innerHTML = `<span class="news-title">${n.title}</span><div style="display:flex; justify-content:space-between; margin-top:0.25rem;"><span style="font-size:0.7rem; color:var(--text-muted);">${n.source}</span><span class="badge ${badgeClass}">${n.sentiment_label}</span></div>`;
            newsArea.appendChild(item);
        });
    } else {
        newsArea.innerHTML = '<p style="text-align:center; padding:1rem; color:var(--text-muted); font-size:0.8rem;">No Intelligence Reports at this Node.</p>';
    }
}

function updateChartUI(data) {
    document.getElementById('last-price').textContent = `${data.currency} ${data.last_price}`;
    const ctx = document.getElementById('stock-chart').getContext('2d');
    if (chart) chart.destroy();

    const grad = ctx.createLinearGradient(0, 0, 0, 400);
    grad.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates.map(d => d.split('-').slice(1).join('/')),
            datasets: [{ data: data.prices, borderColor: '#3b82f6', tension: 0.4, fill: true, backgroundColor: grad, pointRadius: 0, borderWidth: 4 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#64748b' } },
                x: { grid: { display: false }, ticks: { color: '#64748b' } }
            }
        }
    });
}

// Lifecycle Init
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('ticker-input');
    const form = document.getElementById('predict-form');
    
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            runPrediction();
        });
    }
});
