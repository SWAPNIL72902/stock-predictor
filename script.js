/**
 * Terminal.AI v2.0
 * Features: Dotted Grid Canvas, Spotlight Effects, News, and Yahoo Market Data
 */

let marketChart = null;
let currentTicker = "RELIANCE.NS";

// --- BACKGROUND: Dotted Grid Animation ---
function initBackground() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let width, height, dots = [];

    const spacing = 40;
    const dotSize = 1;

    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    }

    window.addEventListener('resize', resize);
    resize();

    function draw() {
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = 'rgba(59, 130, 246, 0.15)';
        
        const time = Date.now() * 0.001;

        for (let x = 0; x < width; x += spacing) {
            for (let y = 0; y < height; y += spacing) {
                // Wave motion calculation
                const dist = Math.sqrt(Math.pow(x - width/2, 2) + Math.pow(y - height/2, 2));
                const wave = Math.sin(dist * 0.01 - time * 2) * 5;
                
                ctx.beginPath();
                ctx.arc(x, y + wave, dotSize, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
}

// --- CORE: Search & Data ---
async function fetchStockData(ticker = currentTicker) {
    // Sanitize ticker: uppercase and fix common typos
    ticker = ticker.trim().toUpperCase().replace("RELAINCE", "RELIANCE");
    currentTicker = ticker;
    
    document.getElementById('active-id').textContent = ticker;
    document.getElementById('live-price').textContent = "Updating...";

    const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?range=1mo&interval=1d`;
    
    // Primary and Secondary Proxies to handle potential downtime/rate-limiting
    const proxies = [
        `https://api.allorigins.win/raw?url=${encodeURIComponent(yahooUrl)}`,
        `https://corsproxy.io/?${encodeURIComponent(yahooUrl)}`
    ];

    let success = false;
    for (const url of proxies) {
        if (success) break;
        try {
            const response = await fetch(url);
            if (!response.ok) continue;
            
            const data = await response.json();
            if (!data.chart || !data.chart.result || !data.chart.result[0]) {
                console.error("Malformed data for:", ticker);
                continue;
            }

            const res = data.chart.result[0];
            const quote = res.indicators.quote[0];
            const prices = quote.close ? quote.close.filter(p => p !== null) : [];
            
            if (prices.length === 0) throw new Error("Empty Price Stream");

            const timestamps = res.timestamp ? res.timestamp.slice(-prices.length) : [];
            const currentPrice = prices[prices.length - 1];
            const currency = res.meta.currency || (ticker.endsWith(".NS") ? "INR" : "USD");

            // UI Updates
            const symbol = currency === "INR" ? "₹" : "$";
            document.getElementById('live-price').textContent = `${symbol} ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            
            updateChart(timestamps, prices);
            updatePrediction(ticker);
            success = true;
        } catch (err) {
            console.warn(`Proxy failed: ${url}`, err);
        }
    }

    if (!success) {
        document.getElementById('live-price').textContent = "Connection Lost";
        // Attempt to show what we have if chart already exists
    }
}

function updateChart(timestamps, prices) {
    const ctx = document.getElementById('market-chart').getContext('2d');
    const labels = timestamps.map(ts => {
        const d = new Date(ts * 1000);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    });

    if (marketChart) marketChart.destroy();

    const gradient = ctx.createLinearGradient(0, 0, 0, 450);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
    gradient.addColorStop(1, 'rgba(3, 7, 18, 0)');

    marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: prices,
                borderColor: '#3b82f6',
                borderWidth: 4,
                tension: 0.4,
                pointRadius: 0,
                fill: true,
                backgroundColor: gradient
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#4b5563', font: { size: 10 } } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#4b5563', font: { size: 10 } } }
            }
        }
    });
}

// Simulated ML Recommendation
function updatePrediction(ticker) {
    const isUp = Math.random() > 0.4;
    const confidence = (Math.random() * 15 + 80).toFixed(1);
    
    const predEl = document.getElementById('prediction-badge');
    const bar = document.getElementById('conf-bar');
    const pct = document.getElementById('conf-pct');

    predEl.textContent = isUp ? 'VAL-UP' : 'VAL-DOWN';
    predEl.className = `prediction-val ${isUp ? 'val-up' : 'val-down'}`;
    
    pct.textContent = `${confidence}%`;
    bar.style.width = `${confidence}%`;
    bar.style.backgroundColor = isUp ? '#10b981' : '#ef4444';

    // Update Intelligence List
    const newsList = document.getElementById('news-list');
    newsList.innerHTML = `
        <div class="news-item">
            <span class="news-title">Institutional Accumulation Detected in ${ticker} Hub</span>
            <div style="font-size:0.7rem; color: #6b7280;">Global Node • High Confidence</div>
        </div>
        <div class="news-item">
            <span class="news-title">Market Sentiment Delta Analysis: Primary Connection Stable</span>
            <div style="font-size:0.7rem; color: #6b7280;">Neural Stream • Medium Confidence</div>
        </div>
    `;
}

// --- SPOTLIGHT: Mouse Glow Effect ---
function initSpotlight() {
    document.addEventListener('mousemove', (e) => {
        const cards = document.querySelectorAll('.glow-card');
        cards.forEach(card => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

// --- REFRESH: Countdown Logic ---
let secondsRemaining = 60;
function startCountdown() {
    const el = document.getElementById('countdown');
    if (!el) return;
    
    clearInterval(window.countdownTimer);
    secondsRemaining = 60;
    el.textContent = secondsRemaining;

    window.countdownTimer = setInterval(() => {
        secondsRemaining--;
        el.textContent = secondsRemaining;
        if (secondsRemaining <= 0) {
            fetchStockData();
        }
    }, 1000);
}

// --- AUTH: Simulated Logic ---
const DB = {
    login: (u, p) => {
        if (u && p) {
            localStorage.setItem('currentUser', u);
            return true;
        }
        return false;
    },
    signup: (u, p) => {
        if (u && p) {
            localStorage.setItem('currentUser', u);
            return true;
        }
        return false;
    },
    logout: () => {
        localStorage.removeItem('currentUser');
        window.location.href = './index.html';
    },
    checkAuth: () => {
        const user = localStorage.getItem('currentUser');
        const path = window.location.pathname;
        const isAuthPage = path.endsWith('index.html') || path.endsWith('/') || path.endsWith('signup.html');
        
        if (!user && !isAuthPage) {
            window.location.href = './index.html';
        } else if (user && isAuthPage) {
            window.location.href = './dashboard.html';
        }
    }
};

// Lifecycle Init
document.addEventListener('DOMContentLoaded', () => {
    DB.checkAuth();
    initBackground();
    initSpotlight();

    // Check if we are on Dashboard
    const tickerEl = document.getElementById('active-id');
    if (tickerEl) {
        fetchStockData();
        startCountdown();
        
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            DB.logout();
        });

        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const val = document.getElementById('search-input').value.trim();
                if (val) {
                    fetchStockData(val.toUpperCase());
                    startCountdown();
                }
            });
        }
    }

    // Check if we are on Login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (DB.login(e.target.username.value, e.target.password.value)) {
                window.location.href = './dashboard.html';
            }
        });
    }

    // Check if we are on Signup
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (DB.signup(e.target.username.value, e.target.password.value)) {
                window.location.href = './dashboard.html';
            }
        });
    }
});
