const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let priceTimer = null;

// Objects to track real-time tick changes and colors
let previousPrices = {};
let tickColors = {};

// NEW: Sorting state
let currentSortColumn = '';
let currentSortDirection = 1; // 1 for Ascending, -1 for Descending

/* ---------- ADD WATCHLIST ---------- */
addBtn.onclick = async () => {
    const name = prompt("New watchlist name:");
    if (!name) return;
    await fetch("/watchlist", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    });
    location.reload();
};

/* ---------- TAB SWITCH & RENAME ---------- */
document.querySelectorAll(".tab[data-id]").forEach(tab => {
    tab.onclick = () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeWatchlist = tab.dataset.id;
        
        // Reset memory when switching to a different watchlist
        previousPrices = {};
        tickColors = {};
        currentSortColumn = '';
        document.querySelectorAll("th[data-sort]").forEach(h => {
            h.innerText = h.innerText.replace(' ▲', '').replace(' ▼', '');
        });
        
        startPriceRefresh();
    };

    tab.ondblclick = async () => {
        const name = prompt("Rename watchlist:", tab.innerText);
        if (!name) return;
        await fetch(`/watchlist/${tab.dataset.id}`, {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name})
        });
        location.reload();
    };
});

/* ---------- NEW: HEADER SORTING CLICK LISTENER ---------- */
document.querySelectorAll("th[data-sort]").forEach(th => {
    th.onclick = () => {
        const col = th.dataset.sort;
        if (currentSortColumn === col) {
            currentSortDirection *= -1; // toggle ascending/descending
        } else {
            currentSortColumn = col;
            currentSortDirection = 1;
        }
        
        // Update sorting arrows on the UI
        document.querySelectorAll("th[data-sort]").forEach(h => {
            h.innerText = h.innerText.replace(' ▲', '').replace(' ▼', '');
        });
        th.innerText += currentSortDirection === 1 ? ' ▲' : ' ▼';
        
        loadPrices(); // Re-render table immediately
    };
});

/* ---------- SEARCH ---------- */
search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(s => {
        const d = document.createElement("div");
        d.className = "suggestion-item";
        d.innerText = s.trading_symbol;
        d.onclick = async () => {
            await fetch(`/add?wid=${activeWatchlist}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(s)
            });
            search.value = "";
            suggestions.innerHTML = "";
            loadPrices();
        };
        suggestions.appendChild(d);
    });
});

/* ---------- NEW: HELPER TO PARSE VOLUME ---------- */
// Converts strings like "1.25M" or "800.00K" back into pure numbers so JS can sort them correctly
function parseVolume(v) {
    if (typeof v !== 'string') return Number(v);
    let val = parseFloat(v);
    if (v.endsWith('B')) return val * 1000000000;
    if (v.endsWith('M')) return val * 1000000;
    if (v.endsWith('K')) return val * 1000;
    return val;
}

/* ---------- LOAD PRICES ---------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    let data = await res.json();
    
    // NEW: Sort the fetched data array before generating HTML
    if (currentSortColumn) {
        data.sort((a, b) => {
            let valA = a[currentSortColumn];
            let valB = b[currentSortColumn];

            // Specifically handle volume parsing
            if (currentSortColumn === 'volume') {
                valA = parseVolume(valA);
                valB = parseVolume(valB);
            }

            // Handle alphabetical string sorting (like Symbol or Company Name)
            if (typeof valA === 'string' && currentSortColumn !== 'volume') {
                return valA.localeCompare(valB) * currentSortDirection;
            }
            
            // Handle standard numbers (like LTP, %, Open, High, Low, Close)
            return (valA - valB) * currentSortDirection;
        });
    }

    tbody.innerHTML = "";

    data.forEach(s => {
        const tv = s.symbol.replace("-EQ", "");
        
        // Determine LTP tick direction
        let ltpClass = tickColors[s.symbol] || ""; 
        
        if (previousPrices[s.symbol] !== undefined) {
            if (s.ltp > previousPrices[s.symbol]) {
                ltpClass = "price-up";
            } else if (s.ltp < previousPrices[s.symbol]) {
                ltpClass = "price-down";
            }
        }
        
        previousPrices[s.symbol] = s.ltp;
        tickColors[s.symbol] = ltpClass;

        const dayClass = s.pct >= 0 ? "price-up" : "price-down";
        
        tbody.innerHTML += `
        <tr onclick="openChart('${tv}')">
            <td>${s.symbol}</td>
            <td>${s.company_name}</td>
            <td class="${ltpClass}">${s.ltp.toFixed(2)}</td>
            <td class="${dayClass}">${s.pct.toFixed(2)}%</td>
            <td>${s.volume}</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td>
                <button onclick="event.stopPropagation(); removeStock('${s.symbol}')">✕</button>
            </td>
        </tr>`;
    });
}

/* ---------- TRADINGVIEW ---------- */
function openChart(sym) {
    window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym}`, "_blank");
}

/* ---------- AUTO REFRESH ---------- */
function startPriceRefresh() {
    if (priceTimer) clearInterval(priceTimer);
    loadPrices();
    priceTimer = setInterval(loadPrices, 5000);
}

async function removeStock(sym) {
    await fetch(`/remove?wid=${activeWatchlist}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: sym})
    });
    
    // Clear the memory for the removed stock
    delete previousPrices[sym];
    delete tickColors[sym];
    
    loadPrices();
}

document.querySelector(".tab[data-id]").classList.add("active");
startPriceRefresh();
