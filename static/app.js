const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let priceTimer = null;

// Objects to track real-time tick changes and colors
let previousPrices = {};
let tickColors = {};

// NEW: State variables for column sorting persistence
let sortCol = null;
let sortAsc = false;

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
        
        // Reset tick memory and sorting when switching watchlists
        previousPrices = {};
        tickColors = {};
        
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

/* ---------- NEW: COLUMN SORTING LOGIC ---------- */
// Helper to convert formatted volume (e.g., "1.5M", "500K") back to numbers for accurate sorting
function parseVolume(volStr) {
    if (!volStr || typeof volStr !== 'string') return 0;
    let num = parseFloat(volStr);
    if (volStr.includes('K')) return num * 1000;
    if (volStr.includes('M')) return num * 1000000;
    if (volStr.includes('B')) return num * 1000000000;
    return num;
}

// Automatically attach click listeners to existing table headers
const colKeys = ["symbol", "company_name", "ltp", "pct", "volume", "open", "high", "low", "close"];
document.querySelectorAll("thead th").forEach((th, index) => {
    if (index < colKeys.length) { // Skip the 'Delete' column
        th.style.cursor = "pointer";
        th.title = "Click to sort";
        
        th.onclick = () => {
            const key = colKeys[index];
            if (sortCol === key) {
                sortAsc = !sortAsc; // Toggle direction if clicking the same column
            } else {
                sortCol = key;
                sortAsc = false; // Default to descending (highest first) for new columns
            }
            
            // Update UI arrows on headers
            document.querySelectorAll("thead th").forEach(el => el.innerText = el.innerText.replace(/ [▲▼]/, ''));
            th.innerText += sortAsc ? " ▲" : " ▼";
            
            loadPrices(); // Re-render immediately without waiting for the 5-second interval
        };
    }
});

/* ---------- LOAD PRICES ---------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    let data = await res.json();
    
    // NEW: Apply sorting before rendering the table
    if (sortCol) {
        data.sort((a, b) => {
            let valA = a[sortCol];
            let valB = b[sortCol];
            
            if (sortCol === "volume") {
                valA = parseVolume(valA);
                valB = parseVolume(valB);
            }
            
            if (valA < valB) return sortAsc ? -1 : 1;
            if (valA > valB) return sortAsc ? 1 : -1;
            return 0;
        });
    }

    tbody.innerHTML = "";

    data.forEach(s => {
        const tv = s.symbol.replace("-EQ", "");
        
        // Determine LTP tick direction (Up or Down compared to 5 seconds ago)
        let ltpClass = tickColors[s.symbol] || ""; 
        
        if (previousPrices[s.symbol] !== undefined) {
            if (s.ltp > previousPrices[s.symbol]) {
                ltpClass = "price-up";
            } else if (s.ltp < previousPrices[s.symbol]) {
                ltpClass = "price-down";
            }
        }
        
        // Save the current state for the next 5-second refresh
        previousPrices[s.symbol] = s.ltp;
        tickColors[s.symbol] = ltpClass;

        // Day change % is always based on overall daily performance
        const dayClass = s.pct >= 0 ? "price-up" : "price-down";
        
        // Render rows
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

// Initialize
document.querySelector(".tab[data-id]").classList.add("active");
startPriceRefresh();
