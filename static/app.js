document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const tableBody = document.getElementById('watchlistBody');

    // --- UTILS ---
    function formatVolume(num) {
        if (num > 10000000) return (num / 10000000).toFixed(2) + 'Cr';
        if (num > 100000) return (num / 100000).toFixed(2) + 'L';
        return num;
    }

    // --- LOAD WATCHLIST ---
    async function fetchWatchlist() {
        try {
            const res = await fetch('/api/watchlist');
            const data = await res.json();
            renderTable(data);
        } catch (e) {
            console.error("Fetch error:", e);
        }
    }

    function renderTable(stocks) {
        tableBody.innerHTML = '';
        stocks.forEach(stock => {
            const tr = document.createElement('tr');
            
            // Color logic
            const colorClass = parseFloat(stock.change) >= 0 ? 'up' : 'down';
            
            tr.innerHTML = `
                <td class="fw-bold">${stock.symbol}</td>
                <td>${stock.name}</td> <td class="${colorClass}">${stock.ltp}</td>
                <td class="${colorClass}">${stock.change}%</td>
                <td>${formatVolume(stock.volume)}</td>
                <td style="font-size: 0.8rem; color: #888;">${stock.ohlc}</td>
                <td class="action-cell" onclick="event.stopPropagation()">
                    <span class="del-btn" data-id="${stock.id}">✕</span>
                </td>
            `;

            // Row Click -> TradingView
            tr.addEventListener('click', () => {
                window.open(`https://www.tradingview.com/chart/?symbol=NSE:${stock.symbol}`, '_blank');
            });

            // Delete Action
            tr.querySelector('.del-btn').addEventListener('click', async (e) => {
                e.stopPropagation(); // Prevent row click
                await fetch(`/api/delete/${stock.id}`, { method: 'DELETE' });
                fetchWatchlist();
            });

            tableBody.appendChild(tr);
        });
    }

    // --- SEARCH LOGIC ---
    searchInput.addEventListener('input', async (e) => {
        const query = e.target.value;
        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }

        const res = await fetch(`/api/search?q=${query}`);
        const results = await res.json();

        searchResults.innerHTML = '';
        if (results.length > 0) {
            searchResults.style.display = 'block';
            results.forEach(item => {
                const div = document.createElement('div');
                div.className = 'dropdown-item';
                div.textContent = `${item.symbol} (${item.token})`;
                div.onclick = async () => {
                    await fetch('/api/add', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(item)
                    });
                    searchInput.value = '';
                    searchResults.style.display = 'none';
                    fetchWatchlist();
                };
                searchResults.appendChild(div);
            });
        } else {
            searchResults.style.display = 'none';
        }
    });

    // Hide dropdown on click outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    // Auto Refresh every 5s
    fetchWatchlist();
    setInterval(fetchWatchlist, 5000);
});
