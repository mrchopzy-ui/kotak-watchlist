const tbody = document.getElementById("watchlist");
const indicesDiv = document.getElementById("indices");
const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");

let lastData = [];

/* ---------- VOLUME FORMAT ---------- */
function formatVolume(v) {
    if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
    if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
    if (v >= 1e3) return (v / 1e3).toFixed(2) + "K";
    return "-";
}

/* ---------- SEARCH + SUGGESTIONS (FIX) ---------- */
search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    const q = search.value.trim();
    if (!q) return;

    const res = await fetch(`/search?q=${q}`);
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

/* ---------- INDICES ---------- */
async function loadIndices() {
    const res = await fetch("/indices");
    const data = await res.json();

    indicesDiv.innerHTML = "";
    data.forEach(i => {
        indicesDiv.innerHTML += `
            <div class="index-card">
                <div class="name">${i.name}</div>
                <div class="price">${i.price.toFixed(2)}</div>
                <div class="pct ${i.pct >= 0 ? 'green' : 'red'}">
                    ${i.pct.toFixed(2)}%
                </div>
            </div>
        `;
    });
}

/* ---------- WATCHLIST ---------- */
async function loadPrices() {
    const res = await fetch("/prices");
    lastData = await res.json();
    render();
}

function render() {
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
