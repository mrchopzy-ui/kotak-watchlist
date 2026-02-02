let lastData = [];
const tbody = document.getElementById("watchlist");
const indicesBox = document.getElementById("indices");

/* ---------- FORMAT ---------- */
function formatVolume(v) {
    if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
    if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(2) + "K";
    return "-";
}

/* ---------- LOAD STOCKS ---------- */
async function loadPrices() {
    const res = await fetch("/prices");
    lastData = await res.json();
    renderTable();
}

/* ---------- LOAD INDICES ---------- */
async function loadIndices() {
    const res = await fetch("/indices");
    const data = await res.json();

    indicesBox.innerHTML = "";
    data.forEach(i => {
        indicesBox.innerHTML += `
        <div class="index-card">
            <div class="name">${i.name}</div>
            <div class="price">${i.ltp.toFixed(2)}</div>
            <div class="${i.change_pct >= 0 ? 'green' : 'red'}">
                ${i.change_pct.toFixed(2)}%
            </div>
        </div>`;
    });
}

/* ---------- TABLE ---------- */
function renderTable() {
    tbody.innerHTML = "";
    lastData.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td>${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td class="${s.change_pct >= 0 ? 'green' : 'red'}">
                ${s.change_pct.toFixed(2)}%
            </td>
            <td>${formatVolume(s.volume)}</td>
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

async function removeStock(symbol) {
    await fetch("/remove", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: symbol})
    });
    loadPrices();
}

setInterval(() => {
    loadPrices();
    loadIndices();
}, 5000);

loadPrices();
loadIndices();
