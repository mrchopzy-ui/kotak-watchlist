const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let timer = null;

/* -------- TradingView search for REAL company name -------- */
async function fetchCompanyName(symbol) {
    const clean = symbol.replace("-EQ", "");
    const r = await fetch(
        `https://symbol-search.tradingview.com/symbol_search/?text=${clean}&exchange=NSE`
    );
    const j = await r.json();
    return j.length ? j[0].description : clean;
}

/* -------- SEARCH -------- */
search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const r = await fetch(`/search?q=${search.value}`);
    const data = await r.json();

    for (const s of data) {
        const div = document.createElement("div");
        div.className = "suggestion-item";
        div.innerText = s.trading_symbol;

        div.onclick = async () => {
            const companyName = await fetchCompanyName(s.trading_symbol);

            await fetch(`/add?wid=${activeWatchlist}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    trading_symbol: s.trading_symbol,
                    exchange_token: s.exchange_token,
                    company_name: companyName
                })
            });

            search.value = "";
            suggestions.innerHTML = "";
            loadPrices();
        };
        suggestions.appendChild(div);
    }
});

/* -------- PRICES -------- */
async function loadPrices() {
    const r = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await r.json();
    tbody.innerHTML = "";

    data.forEach(s => {
        const tv = s.symbol.replace("-EQ", "");
        tbody.innerHTML += `
        <tr onclick="window.open('https://www.tradingview.com/chart/?symbol=NSE:${tv}')">
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

/* -------- AUTO REFRESH -------- */
loadPrices();
timer = setInterval(loadPrices, 5000);
