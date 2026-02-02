let sortColumn = null;
let sortAsc = true;
let lastData = [];

const tbody = document.getElementById("watchlist");

function formatVolume(v) {
    if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
    if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(2) + "K";
    return "-";
}

function sortBy(col) {
    sortAsc = sortColumn === col ? !sortAsc : true;
    sortColumn = col;
    render();
}

function render() {
    let data = [...lastData];

    if (sortColumn) {
        data.sort((a, b) =>
            sortAsc ? a[sortColumn] - b[sortColumn]
                    : b[sortColumn] - a[sortColumn]
        );
    }

    tbody.innerHTML = "";

    data.forEach(s => {
        tbody.innerHTML += `
        <tr class="${s.is_index ? 'index-row' : ''}">
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
            <td>${s.is_index ? "-" : `<button class="delete" onclick="removeStock('${s.symbol}')">✕</button>`}</td>
        </tr>`;
    });
}

async function loadPrices() {
    const res = await fetch("/prices");
    lastData = await res.json();
    render();
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
