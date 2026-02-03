const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let timer = null;

search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const r = await fetch(`/search?q=${search.value}`);
    const data = await r.json();

    data.forEach(s => {
        const d = document.createElement("div");
        d.className = "suggestion-item";
        d.innerText = s.trading_symbol;

        d.onclick = async () => {
            await fetch(`/add?wid=${activeWatchlist}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    trading_symbol: s.trading_symbol,
                    company_name: s.company_name,
                    exchange_token: s.exchange_token
                })
            });
            suggestions.innerHTML = "";
            search.value = "";
            loadPrices();
        };
        suggestions.appendChild(d);
    });
});

async function loadPrices() {
    const r = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await r.json();
    tbody.innerHTML = "";

    data.forEach(s => {
        tbody.innerHTML += `
        <tr onclick="window.open('https://www.tradingview.com/chart/?symbol=NSE:${s.symbol.replace("-EQ","")}', '_blank')">
            <td>${s.symbol}</td>
            <td>${s.company_name}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td>${s.pct.toFixed(2)}%</td>
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

async function removeStock(sym) {
    await fetch(`/remove?wid=${activeWatchlist}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: sym})
    });
    loadPrices();
}

function start() {
    loadPrices();
    timer = setInterval(loadPrices, 5000);
}

start();
