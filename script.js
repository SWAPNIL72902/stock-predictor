/**
 * Terminal.AI Core Logic
 * Handles real-time market data extraction, Chart.js rendering, and auto-refresh.
 */

let marketChart = null;
const TICKER = "RELIANCE.NS";
const TICKER_NAME = "RELIANCE.NS";

async function fetchStockData() {
    console.log(`[Terminal.AI] Node Syncing: ${TICKER}...`);
    
    // Yahoo Finance URL via AllOrigins proxy to bypass CORS
    const proxyUrl = "https://api.allorigins.win/raw?url=";
    const targetUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${TICKER}?range=1mo&interval=1d`;
    const finalUrl = `${proxyUrl}${encodeURIComponent(targetUrl)}`;

    try {
        const response = await fetch(finalUrl);
        if (!response.ok) throw new Error("CORS Protocol Failed");
        
        const data = await response.json();
        const result = data.chart.result[0];
        
        // 1. Extract Metadata
        const quote = result.indicators.quote[0];
        const timestamps = result.timestamp;
        const prices = quote.close;
        const currentPrice = prices[prices.length - 1];
        const currency = result.meta.currency;

        // 2. Update Header Price
        updateHeaderPrice(currentPrice, currency);

        // 3. Update Chart
        updateChart(timestamps, prices);

        console.log(`[Terminal.AI] Node Refreshed. Current: ${currentPrice} ${currency}`);
    } catch (err) {
        console.error("[Terminal.AI] Sync Error:", err);
        document.getElementById('live-price').textContent = "Data unavailable";
    }
}

function updateHeaderPrice(price, currency) {
    const el = document.getElementById('live-price');
    const symbol = currency === 'INR' ? '₹' : '$';
    el.textContent = `${symbol} ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function updateChart(timestamps, prices) {
    const ctx = document.getElementById('market-chart').getContext('2d');
    
    // Prepare Labels (Convert timestamps to Dates)
    const labels = timestamps.map(ts => {
        const d = new Date(ts * 1000);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    });

    if (marketChart) marketChart.destroy();

    // Chart Gradient Styling
    const gradient = ctx.createLinearGradient(0, 0, 0, 450);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
    gradient.addColorStop(1, 'rgba(15, 23, 42, 0)');

    marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Market Price',
                data: prices,
                borderColor: '#3b82f6',
                borderWidth: 4,
                tension: 0.4, // Smooth curve
                pointRadius: 0, // Clean look
                pointHoverRadius: 6,
                fill: true,
                backgroundColor: gradient
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#fff',
                    bodyColor: '#94a3b8',
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `Price: ${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b', font: { size: 10 } }
                }
            }
        }
    });
}

// Initial Sync + Auto-Refresh Protocol
document.addEventListener('DOMContentLoaded', () => {
    fetchStockData();
    
    // Refresh every 60 seconds
    setInterval(fetchStockData, 60000);
});
