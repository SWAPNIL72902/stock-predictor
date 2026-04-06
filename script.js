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
        const isAuthPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/') || window.location.pathname.endsWith('signup.html');
        
        if (!user && !isAuthPage) {
            window.location.href = './index.html';
        } else if (user && isAuthPage) {
            window.location.href = './dashboard.html';
        }
    }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    DB.checkAuth();

    // Login Handling
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const u = e.target.username.value;
            const p = e.target.password.value;
            if (DB.login(u, p)) window.location.href = './dashboard.html';
        });
    }

    // Signup Handling
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const u = e.target.username.value;
            const p = e.target.password.value;
            if (DB.signup(u, p)) window.location.href = './dashboard.html';
        });
    }

    // Dashboard Handling
    const predictForm = document.getElementById('predictForm');
    if (predictForm) {
        predictForm.addEventListener('submit', (e) => {
            e.preventDefault();
            runPrediction();
        });
        
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) logoutBtn.addEventListener('click', DB.logout);
    }
});

// --- Dashboard Logic (Simulated) ---
async function runPrediction() {
    const input = document.getElementById('tickerInput');
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;

    const loader = document.getElementById('loader');
    const results = document.getElementById('resultsArea');
    const btn = document.getElementById('predictBtn');
    const btnText = document.getElementById('btnText');

    // Enter Loading State
    btn.disabled = true;
    btnText.textContent = 'Analysing Neural Nodes...';
    results.classList.add('hidden');
    loader.classList.remove('hidden');

    try {
        // Simulate API Delay
        await new Promise(r => setTimeout(r, 1500));

        // Mock data
        const isUp = Math.random() > 0.5;
        const confidence = (Math.random() * 20 + 75).toFixed(1);
        
        updateUI(ticker, isUp, confidence);

        loader.classList.add('hidden');
        results.classList.remove('hidden');
    } catch (err) {
        console.error(err);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Run Neural Forecast';
    }
}

function updateUI(ticker, isUp, confidence) {
    document.getElementById('activeTicker').textContent = ticker;
    const predEl = document.getElementById('predictionValue');
    predEl.textContent = isUp ? 'VAL-UP ' : 'VAL-DOWN';
    predEl.className = `prediction-val ${isUp ? 'val-up' : 'val-down'}`;

    document.getElementById('confPct').textContent = `${confidence}%`;
    document.getElementById('confBar').style.width = `${confidence}%`;

    const newsList = document.getElementById('newsList');
    newsList.innerHTML = `
        <div class="news-item">
            <span class="news-title">Institutional Accumulation Detected in ${ticker} Node</span>
            <div class="news-meta">Global Intelligence Feed • High Impact</div>
        </div>
        <div class="news-item">
            <span class="news-title">Whale Transaction Movement for ${ticker} Establish Connection</span>
            <div class="news-meta">Node Delta • Medium Impact</div>
        </div>
    `;
}
