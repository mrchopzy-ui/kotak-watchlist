const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");
const modal = document.getElementById("chartModal");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let priceTimer = null;

let previousPrices = {};
let tickColors = {};

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

/* ---------- LOAD PRICES ---------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await res.json();
    if (!data) return;
    tbody.innerHTML = "";

    data.forEach(s => {
        const tvSym = s.symbol.replace("-EQ", "");
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
        <tr onclick="openChart('${tvSym}', '${s.company_name}')">
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

/* ---------- NEW: EMBEDDED CHART LOGIC ---------- */
function openChart(sym, name) {
    document.getElementById("modalTitle").innerText = `NSE: ${name}`;
    const container = document.getElementById("tv-container");
    
    // Create the TradingView Iframe
    container.innerHTML = `
        <iframe 
            src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_762ae&symbol=NSE:${sym}&interval=D&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Asia/Kolkata&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&locale=en"
            width="100%" 
            height="100%" 
            frameborder="0" 
            allowtransparency="true" 
            scrolling="no" 
            allowfullscreen>
        </iframe>`;
    
    modal.style.display = "block";
}

function closeChart() {
    modal.style.display = "none";
    document.getElementById("tv-container").innerHTML = ""; // Stop the iframe
}

// Close modal if user clicks outside of the box
window.onclick = (event) => {
    if (event.target == modal) closeChart();
};

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
    delete previousPrices[sym];
    delete tickColors[sym];
    loadPrices();
}

document.querySelector(".tab[data-id]").classList.add("active");
startPriceRefresh();
