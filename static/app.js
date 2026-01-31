let selectedStock = null;

const searchInput = document.getElementById("search");
const suggestionsDiv = document.getElementById("suggestions");
const addBtn = document.getElementById("addBtn");
const watchlistBody = document.getElementById("watchlist");

searchInput.addEventListener("input", async () => {
    const q = searchInput.value.trim();
    suggestionsDiv.innerHTML = "";
    selectedStock = null;
    addBtn.disabled = true;

    if (!q) return;

    const res = await fetch(`/search?q=${q}`);
    const data = await res.json();

    data.forEach(stock => {
        const div = document.createElement("div");
        div.textContent = stock.trading_symbol;
        div.onclick = () => {
            selectedStock = stock;
            searchInput.value = stock.trading_symbol;
            suggestionsDiv.innerHTML = "";
            addBtn.disabled = false;
        };
        suggestionsDiv.appendChild(div);
    });
});

addBtn.onclick = async () => {
    await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(selectedStock)
    });
    searchInput.value = "";
    addBtn.disabled = true;
    loadPrices();
};

function openChart(symbol) {
    const tvSymbol = `NSE:${symbol.replace("-EQ", "")}`;
    window.open(
        `https://www.tradingview.com/chart/?symbol=${tvSymbol}`,
        "_blank"
    );
}

async function loadPrices() {
    const res = await fetch("/prices");
    const data = await res.json();
    watchlistBody.innerHTML = "";

    data.forEach(s => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td class="link" onclick="openChart('${s.symbol}')">
                ${s.symbol}
            </td>
            <td>${s.company}</td>
            <td>${s.ltp}</td>
            <td class="${s.change_pct >= 0 ? 'green' : 'red'}">
                ${s.change_pct}%
            </td>
            <td>
                <button onclick="removeStock('${s.symbol}')">❌</button>
            </td>
        `;

        watchlistBody.appendChild(tr);
    });
}

async function removeStock(symbol) {
    await fetch("/remove", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: symbol})
    });
    loadPrices();
}

setInterval(loadPrices, 5000);
loadPrices();
