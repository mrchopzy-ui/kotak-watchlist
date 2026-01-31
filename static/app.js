let activeTab = "";
let selectedStock = null;

const tabsDiv = document.getElementById("tabs");
const watchlistBody = document.getElementById("watchlist");
const searchInput = document.getElementById("search");
const addBtn = document.getElementById("addBtn");
const suggestionsDiv = document.getElementById("suggestions");

async function loadTabs() {
    const res = await fetch("/tabs");
    const tabs = await res.json();
    tabsDiv.innerHTML = "";

    tabs.forEach((t, i) => {
        const b = document.createElement("button");
        b.textContent = t;
        b.onclick = () => switchTab(t);
        if (i === 0) switchTab(t);
        tabsDiv.appendChild(b);
    });
}

function switchTab(tab) {
    activeTab = tab;
    loadPrices();
}

searchInput.oninput = async () => {
    const q = searchInput.value.trim();
    suggestionsDiv.innerHTML = "";
    selectedStock = null;
    addBtn.disabled = true;

    if (!q) return;

    const res = await fetch(`/search?q=${q}`);
    const data = await res.json();

    data.forEach(s => {
        const d = document.createElement("div");
        d.textContent = s.trading_symbol;
        d.onclick = () => {
            selectedStock = s;
            searchInput.value = s.trading_symbol;
            suggestionsDiv.innerHTML = "";
            addBtn.disabled = false;
        };
        suggestionsDiv.appendChild(d);
    });
};

addBtn.onclick = async () => {
    await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tab: activeTab, stock: selectedStock})
    });
    searchInput.value = "";
    addBtn.disabled = true;
    loadPrices();
};

async function loadPrices() {
    const res = await fetch(`/prices/${activeTab}`);
    const data = await res.json();
    watchlistBody.innerHTML = "";

    data.forEach(s => {
        watchlistBody.innerHTML += `
        <tr>
            <td onclick="openChart('${s.symbol}')" class="link">${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp}</td>
            <td class="${s.change_pct>=0?'green':'red'}">${s.change_pct}%</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td><button onclick="removeStock('${s.symbol}')">❌</button></td>
        </tr>`;
    });
}

async function removeStock(symbol) {
    await fetch("/remove", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tab: activeTab, symbol})
    });
    loadPrices();
}

function openChart(sym) {
    window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym.replace("-EQ","")}`, "_blank");
}

setInterval(loadPrices, 5000);
loadTabs();
