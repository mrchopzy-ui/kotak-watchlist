let currentWatchlistId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadWatchlists();
    fetchMarketIndices();
    setInterval(fetchMarketIndices, 30000); 
});

// --- MARKET INDICATORS ---
async function fetchMarketIndices() {
    try {
        const res = await fetch('/api/market_indices');
        const data = await res.json();
        const container = document.getElementById('indices-bar');
        container.innerHTML = data.map(idx => `
            <div class="index-card">
                <span style="color:var(--text-secondary)">${idx.name}</span>
                <span style="margin-left:8px; font-weight:bold">${idx.price}</span>
                <span class="${idx.change.includes('+') ? 'change-pos' : 'change-neg'}" style="margin-left:5px">
                    ${idx.change}
                </span>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

// --- WATCHLIST MANAGEMENT ---
async function loadWatchlists() {
    const res = await fetch('/api/watchlists');
    const lists = await res.json();
    const container = document.getElementById('watchlist-tabs');
    container.innerHTML = '';

    lists.forEach((list, idx) => {
        const tab = document.createElement('div');
        tab.className = `tab ${currentWatchlistId === list.id || (!currentWatchlistId && idx === 0) ? 'active' : ''}`;
        tab.innerText = list.name;
        tab.onclick = () => { currentWatchlistId = list.id; loadWatchlists(); };
        tab.ondblclick = () => renameWatchlist(list.id, list.name);
        container.appendChild(tab);
        if (!currentWatchlistId && idx === 0) currentWatchlistId = list.id;
    });
    loadStocks();
}

async function renameWatchlist(id, oldName) {
    const newName = prompt("New name:", oldName);
    if (newName && newName !== oldName) {
        await fetch(`/api/watchlists/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: newName})
        });
        loadWatchlists();
    }
}

document.getElementById('add-watchlist-btn').onclick = async () => {
    const name = prompt("Watchlist Name:");
    if (name) {
        await fetch('/api/watchlists', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name})
        });
        loadWatchlists();
    }
};

// --- SEARCH ---
const searchInput = document.getElementById('stock-search');
const resultsDiv = document.getElementById('search-results');

searchInput.oninput = async () => {
    const q = searchInput.value;
    if (q.length < 2) { resultsDiv.innerHTML = ''; return; }
    const res = await fetch(`/api/search?q=${q}`);
    const data = await res.json();
    resultsDiv.innerHTML = data.map(item => `
        <div class="autocomplete-item" onclick="addStock('${item.symbol}', '${item.instrument_token}', '${item.name.replace(/'/g, "")}')">
            ${item.symbol} <small style="color:gray">${item.name}</small>
        </div>
    `).join('');
};

async function addStock(symbol, token, name) {
    await fetch('/api/stocks', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            watchlist_id: currentWatchlistId,
            symbol: symbol,
            token: token,
            company_name: name
        })
    });
    searchInput.value = '';
    resultsDiv.innerHTML = '';
    loadStocks();
}

// --- TABLE & TRADINGVIEW ---
async function loadStocks() {
    if (!currentWatchlistId) return;
    const res = await fetch(`/api/stocks?watchlist_id=${currentWatchlistId}`);
    const stocks = await res.json();
    
    const tokens = stocks.map(s => s.token).join(',');
    const qRes = await fetch(`/api/quotes?tokens=${tokens}`);
    const quotes = await qRes.json();

    const tbody = document.getElementById('stock-list-body');
    tbody.innerHTML = stocks.map(s => {
        const q = quotes[s.token] || {ltp:0, change:0, vol:'0', open:0, high:0, low:0, close:0};
        return `
            <tr>
                <td>
                    <a href="https://www.tradingview.com/chart/?symbol=NSE:${s.symbol}" 
                       target="_blank" class="symbol-link">
                       ${s.symbol} ↗
                    </a>
                </td>
                <td style="font-size:0.75rem; color:var(--text-secondary)">${s.company}</td>
                <td>${q.ltp.toFixed(2)}</td>
                <td class="${q.change >= 0 ? 'change-pos' : 'change-neg'}">${q.change.toFixed(2)}%</td>
                <td>${q.vol}</td>
                <td>${q.open}</td>
                <td>${q.high}</td>
                <td>${q.low}</td>
                <td>${q.close}</td>
                <td><button class="btn-delete" onclick="deleteStock(${s.id})">❌</button></td>
            </tr>
        `;
    }).join('');
}

async function deleteStock(id) {
    if (confirm("Remove stock?")) {
        await fetch(`/api/stocks/${id}`, { method: 'DELETE' });
        loadStocks();
    }
}

// --- SORTING ---
function sortTable(n) {
    const table = document.getElementById("stock-table");
    let rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
    switching = true;
    dir = "asc"; 
    while (switching) {
        switching = false;
        rows = table.rows;
        for (i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;
            x = rows[i].getElementsByTagName("TD")[n];
            y = rows[i + 1].getElementsByTagName("TD")[n];
            
            let xVal = x.innerText.toLowerCase();
            let yVal = y.innerText.toLowerCase();

            if (n >= 2 && n <= 8) { // Numeric columns
                xVal = parseFloat(xVal.replace(/[^\d.-]/g, '')) || 0;
                yVal = parseFloat(yVal.replace(/[^\d.-]/g, '')) || 0;
            }

            if (dir == "asc") {
                if (xVal > yVal) { shouldSwitch = true; break; }
            } else {
                if (xVal < yVal) { shouldSwitch = true; break; }
            }
        }
        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            switchcount ++;
        } else if (switchcount == 0 && dir == "asc") {
            dir = "desc";
            switching = true;
        }
    }
}
