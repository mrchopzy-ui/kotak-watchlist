let sortColumn = null;
let sortAsc = true;
let lastData = [];

const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");

/* ---------- SEARCH (SYMBOL ONLY) ---------- */

search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(stock => {
        const div = document.createElement("div");
        div.className = "suggestion-item";
        div.innerHTML = `<strong>${stock.trading_symbol}</strong>`;

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

/* ---------- SORT ---------- */

function sortBy(col) {
    sortAsc = sortColumn === col ? !sortAsc : true;
    sortColumn = col;
    renderTable();
}

/* ---------- TABLE ---------- */

function renderTable() {
    let data = [...lastData];

    if (sortColumn) {
        data.sort((a, b) => {
            let x = a[sortColumn];
            let y = b[sortColumn];
            return sortAsc ? (x > y ? 1 : -1) : (x < y ? 1 : -1);
        });
    }

    tbody.innerHTML = "";

    data.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td class="link">${s.symbol}</td>
            <td class="company">${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td class="${s.change_pct >= 0 ? 'green' : 'red'}">
                ${s.change_pct.toFixed(2)}%
            </td>
            <td>${s.open.toFixed(2)}</td>
            <td>${s.high.toFixed(2)}</td>
            <td>${s.low.toFixed(2)}</td>
            <td>${s.close.toFixed(2)}</td>
            <td>
                <button class="delete" onclick="removeStock('${s.symbol}')">✕</button>
            </td>
        </tr>`;
    });
}

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
