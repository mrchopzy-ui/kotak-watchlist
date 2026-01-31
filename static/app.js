let sortColumn = null;
let sortAsc = true;
let lastData = [];

const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");

/* ---------------- SEARCH & AUTO-ADD ---------------- */

search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(stock => {
        const div = document.createElement("div");
        div.className = "suggestion-item";
        div.innerHTML = `
            <strong>${stock.trading_symbol}</strong>
            <span>${stock.company_name}</span>
        `;

        div.onclick = async () => {
            await fetch("/add", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(stock)
            });
            search.value = "";
            suggestions.innerHTML = "";
            loadPrices();
        };

        suggestions.appendChild(div);
    });
});

/* ---------------- TABS ---------------- */

function switchTab(tab) {
    fetch("/set-tab", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tab})
    }).then(() => location.reload());
}

function createTab() {
    const name = prompt("New watchlist name:");
    if (!name) return;

    fetch("/new-tab", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    }).then(() => location.reload());
}

/* ---------------- SORTING ---------------- */

function sortBy(column) {
    if (sortColumn === column) {
        sortAsc = !sortAsc;
    } else {
        sortColumn = column;
        sortAsc = true;
    }
    renderTable();
}

/* ---------------- RENDER ---------------- */

function openChart(symbol) {
    window.open(
        `https://www.tradingview.com/chart/?symbol=NSE:${symbol.replace("-EQ","")}`,
        "_blank"
    );
}

function renderTable() {
    let data = [...lastData];

    if (sortColumn) {
        data.sort((a, b) => {
            let x = a[sortColumn];
            let y = b[sortColumn];

            if (typeof x === "string") {
                x = x.toLowerCase();
                y = y.toLowerCase();
            }

            return sortAsc ? (x > y ? 1 : -1) : (x < y ? 1 : -1);
        });
    }

    tbody.innerHTML = "";

    data.forEach(s => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="link" onclick="openChart('${s.symbol}')">${s.symbol}</td>
            <td class="company">${s.company}</td>
            <td>${s.ltp}</td>
            <td class="${s.change_pct >= 0 ? 'green' : 'red'}">${s.change_pct}%</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td>
                <button class="delete" onclick="removeStock('${s.symbol}')">✕</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

/* ---------------- DATA ---------------- */

async function loadPrices() {
    const res = await fetch("/prices");
    lastData = await res.json();
    renderTable();
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
