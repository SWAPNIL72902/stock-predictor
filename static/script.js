// --- Common Utilities ---
function getToken() { return localStorage.getItem('token'); }

async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);

    const res = await fetch(endpoint, config);
    if (res.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/';
        return null;
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'API request failed');
    return data;
}

// --- Dashboard Logic ---
let dashboardChart = null;

async function runPrediction() {
    const tickerInput = document.getElementById('tickerInput');
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) return;

    const loader = document.getElementById('loader');
    const resultsGrid = document.getElementById('resultsGrid');
    const dashboardHeader = document.getElementById('dashboardHeader');
    const btnText = document.getElementById('btnText');
    const errorBox = document.getElementById('errorBox');

    // Prevent double calls
    const btn = document.getElementById('predictBtn');
    if (btn.disabled) return;

    // 1. Start loading
    btn.disabled = true;
    btnText.textContent = 'Analyzing...';
    errorBox.classList.add('hidden');
    resultsGrid.classList.add('hidden');
    dashboardHeader.classList.add('hidden');
    loader.classList.remove('hidden');

    try {
        // 2. Fetch data
        const [predData, chartData] = await Promise.all([
            apiCall(`/predict?ticker=${ticker}`, 'POST'),
            apiCall(`/stock-data?ticker=${ticker}`)
        ]);

        // 3. Update UI
        updatePredictionUI(predData);
        updateChartUI(chartData);

        // 4. Show results
        dashboardHeader.classList.remove('hidden');
        resultsGrid.classList.remove('hidden');
    } catch (err) {
        console.error(err);
        errorBox.textContent = err.message;
        errorBox.classList.remove('hidden');
    } finally {
        // 5. Cleanup
        loader.classList.add('hidden');
        btn.disabled = false;
        btnText.textContent = 'Run Neural Forecast';
    }
}

function updatePredictionUI(data) {
    document.getElementById('activeTicker').textContent = data.ticker;
    const badge = document.getElementById('predictionBadge');
    badge.textContent = data.prediction;
    badge.className = `prediction-badge ${data.prediction === 'UP' ? 'badge-up' : 'badge-down'}`;

    document.getElementById('confidencePct').textContent = `${(data.confidence * 100).toFixed(1)}%`;
    document.getElementById('confidenceBar').style.width = `${(data.confidence * 100)}%`;

    const sentLabel = document.getElementById('sentLabel');
    sentLabel.textContent = data.sentiment_label || 'Neutral';
    sentLabel.className = `sentiment-badge ${data.sentiment_label === 'Positive' ? 'sent-pos' : data.sentiment_label === 'Negative' ? 'sent-neg' : 'sent-neu'}`;

    const newsList = document.getElementById('newsList');
    newsList.innerHTML = '';
    if (data.news && data.news.length > 0) {
        data.news.forEach(n => {
            const div = document.createElement('div');
            div.className = 'news-item';
            div.innerHTML = `<div class="news-title">${n.title}</div><div class="news-meta">${n.source} • ${n.sentiment_label}</div>`;
            newsList.appendChild(div);
        });
    } else {
        newsList.innerHTML = '<p style="color:var(--text-muted); font-size:0.875rem;">No recent intelligence reports.</p>';
    }
}

function updateChartUI(data) {
    document.getElementById('lastPrice').textContent = `${data.currency} ${data.last_price}`;
    const ctx = document.getElementById('stockChart').getContext('2d');
    if (dashboardChart) dashboardChart.destroy();

    const grad = ctx.createLinearGradient(0, 0, 0, 400);
    grad.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    dashboardChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates.map(d => d.split('-').slice(1).join('/')),
            datasets: [{
                data: data.prices,
                borderColor: '#3b82f6',
                borderWidth: 3,
                tension: 0.4,
                pointRadius: 0,
                fill: true,
                backgroundColor: grad
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#64748b' } },
                x: { grid: { display: false }, ticks: { color: '#64748b' } }
            }
        }
    });
}

// --- Auth Handling ---
async function handleFormSubmit(e, type) {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    const spinner = btn.querySelector('.spinner');
    const btnText = btn.querySelector('.btn-text-content');
    const alert = document.getElementById('authAlert');

    const username = e.target.username.value;
    const password = e.target.password.value;

    btn.disabled = true;
    spinner.classList.remove('hidden');
    alert.classList.add('hidden');

    try {
        const data = await apiCall(type === 'login' ? '/login' : '/signup', 'POST', { username, password });
        if (data) {
            localStorage.setItem('token', data.access_token);
            window.location.href = '/dashboard';
        }
    } catch (err) {
        alert.textContent = err.message;
        alert.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}

// --- Lifecycle ---
document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;

    // Login/Signup setup
    const loginForm = document.getElementById('loginForm');
    if (loginForm) loginForm.addEventListener('submit', (e) => handleFormSubmit(e, 'login'));

    const signupForm = document.getElementById('signupForm');
    if (signupForm) signupForm.addEventListener('submit', (e) => handleFormSubmit(e, 'signup'));

    // Dashboard setup
    const predictForm = document.getElementById('predictForm');
    if (predictForm) {
        if (!getToken()) window.location.href = '/';
        predictForm.addEventListener('submit', (e) => {
            e.preventDefault();
            runPrediction();
        });
        runPrediction(); // Initial load for default AAPL
    }

    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('token');
            window.location.href = '/';
        });
    }
});
