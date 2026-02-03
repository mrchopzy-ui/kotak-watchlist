const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let priceTimer = null;

function openChart(symbol) {
    const clean = symbol.replace("-EQ", "");
    window.open(`https://www.tradingview.com/chart/?symbol=NSE:${clean}`, "_blank");
}

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

/* ---------- TABS ---------- */
document.querySelectorAll(".tab[data-id]").forEach(tab => {
    tab.onclick = () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeWatchlist = tab.dataset.id;
        startPriceRefresh();
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
        d.innerText = `${s.trading_symbol} — ${s.company_name}`;
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

/* ---------- PRICES ---------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await res.json();
    tbody.innerHTML = "";

    data.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td class="clickable" onclick="openChart('${s.symbol}')">${s.symbol}</td>
            <td class="clickable" onclick="openChart('${s.symbol}')">${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td>${s.pct.toFixed(2)}%</td>
            <td>${s.volume}</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td><button onclick="removeStock('${s.symbol}')">✕</button></td>
        </tr>`;
    });
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
    loadPrices();
}

document.querySelector(".tab[data-id]").classList.add("active");
startPriceRefresh();
