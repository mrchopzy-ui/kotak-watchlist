let lastData = [];
let sortCol = null;
let asc = true;

function fmtVol(v) {
    if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
    if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(2) + "K";
    return v;
}

function sortBy(c) {
    asc = sortCol === c ? !asc : true;
    sortCol = c;
    render();
}

function render() {
    let d = [...lastData];
    if (sortCol) {
        d.sort((a, b) => asc ? a[sortCol] - b[sortCol] : b[sortCol] - a[sortCol]);
    }

    const tbody = document.getElementById("watchlist");
    tbody.innerHTML = "";

    d.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td>${s.symbol}</td>
            <td class="company">${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td class="${s.change_pct >= 0 ? 'green' : 'red'}">${s.change_pct.toFixed(2)}%</td>
            <td>${s.open.toFixed(2)}</td>
            <td>${s.high.toFixed(2)}</td>
            <td>${s.low.toFixed(2)}</td>
            <td>${s.close.toFixed(2)}</td>
            <td>${fmtVol(s.volume)}</td>
            <td><button class="delete" onclick="removeStock('${s.symbol}')">✕</button></td>
        </tr>`;
    });
}

async function loadPrices() {
    const r = await fetch("/prices");
    lastData = await r.json();
    render();
}

async function removeStock(sym) {
    await fetch("/remove", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: sym})
    });
    loadPrices();
}

setInterval(loadPrices, 5000);
loadPrices();
