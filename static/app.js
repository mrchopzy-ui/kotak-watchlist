const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;

/* ---------- AUTO REFRESH ---------- */
setInterval(() => {
    loadPrices();
}, 5000);

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

/* ---------- TAB SWITCH ---------- */
document.querySelectorAll(".tab[data-id]").forEach(tab => {
    tab.onclick = () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeWatchlist = tab.dataset.id;
        loadPrices();
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

/* ---------- LOAD PRICES ---------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await res.json();
    tbody.innerHTML = "";

    data.forEach(s => {
        const tv = `https://www.tradingview.com/chart/?symbol=NSE:${s.tv}`;
        tbody.innerHTML += `
        <tr>
            <td><a href="${tv}" target="_blank">${s.symbol}</a></td>
            <td><a href="${tv}" target="_blank">${s.company}</a></td>
            <td>${s.ltp.toFixed(2)}</td>
            <td>${s.pct.toFixed(2)}%</td>
            <td>${s.volume}</td>
            <td><button onclick="removeStock('${s.symbol}')">✕</button></td>
        </tr>`;
    });
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
loadPrices();
