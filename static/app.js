let lastData = [];
let sortColumn = null;
let sortAsc = true;

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
            sortAsc ? a[sortColumn] - b[sortColumn] : b[sortColumn] - a[sortColumn]
        );
    }

    document.getElementById("watchlist").innerHTML =
        data.map(s => `
        <tr>
            <td>${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td class="${s.change_pct >= 0 ? 'green' : 'red'}">${s.change_pct.toFixed(2)}%</td>
            <td>${formatVolume(s.volume)}</td>
            <td>${s.open.toFixed(2)}</td>
            <td>${s.high.toFixed(2)}</td>
            <td>${s.low.toFixed(2)}</td>
            <td>${s.close.toFixed(2)}</td>
            <td><button class="delete" onclick="removeStock('${s.symbol}')">✕</button></td>
        </tr>`).join("");
}

async function loadPrices() {
    lastData = await (await fetch("/prices")).json();
    render();
}

async function loadIndices() {
    const data = await (await fetch("/indices")).json();
    document.getElementById("indices").innerHTML =
        data.map(i => `
        <div class="index-card">
            <div>${i.name}</div>
            <strong>${i.ltp.toFixed(2)}</strong>
            <span class="${i.change_pct >= 0 ? 'green' : 'red'}">
                ${i.change_pct.toFixed(2)}%
            </span>
        </div>`).join("");
}

setInterval(() => {
    loadPrices();
    loadIndices();
}, 5000);

loadPrices();
loadIndices();
