let selectedStock = null;

const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const addBtn = document.getElementById("addBtn");
const tbody = document.getElementById("watchlist");

search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    selectedStock = null;
    addBtn.disabled = true;

    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(s => {
        const d = document.createElement("div");
        d.textContent = s.trading_symbol;
        d.onclick = () => {
            selectedStock = s;
            search.value = s.trading_symbol;
            suggestions.innerHTML = "";
            addBtn.disabled = false;
        };
        suggestions.appendChild(d);
    });
});

addBtn.onclick = async () => {
    await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(selectedStock)
    });
    search.value = "";
    addBtn.disabled = true;
    loadPrices();
};

function switchTab(tab) {
    fetch("/set-tab", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tab})
    }).then(() => location.reload());
}

function createTab() {
    const name = prompt("Watchlist name:");
    if (!name) return;
    fetch("/new-tab", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    }).then(() => location.reload());
}

function openChart(sym) {
    window.open(
        `https://www.tradingview.com/chart/?symbol=NSE:${sym.replace("-EQ","")}`,
        "_blank"
    );
}

async function loadPrices() {
    const res = await fetch("/prices");
    const data = await res.json();
    tbody.innerHTML = "";

    data.forEach(s => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="link" onclick="openChart('${s.symbol}')">${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp}</td>
            <td class="${s.change_pct>=0?'green':'red'}">${s.change_pct}%</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td><button onclick="removeStock('${s.symbol}')">❌</button></td>
        `;
        tbody.appendChild(tr);
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
