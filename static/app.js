const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let timer = null;
let lastPrices = {};

addBtn.onclick = async () => {
    const name = prompt("New watchlist name:");
    if (!name) return;

    await fetch("/watchlist", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    });
    location.reload();
};

document.querySelectorAll(".tab[data-id]").forEach(tab => {
    tab.onclick = () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        activeWatchlist = tab.dataset.id;
        lastPrices = {};
        start();
    };

    tab.ondblclick = async () => {
        const name = prompt("Rename watchlist:", tab.innerText);
        if (!name) return;

        await fetch(`/watchlist/${tab.dataset.id}`, {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name})
        });
        location.reload();
    };
});

search.oninput = async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(s => {
        const d = document.createElement("div");
        d.className = "suggestion-item";
        d.innerText = s.trading_symbol;
        d.onclick = async () => {
            await fetch(`/add?wid=${activeWatchlist}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(s)
            });
            search.value = "";
            suggestions.innerHTML = "";
            load();
        };
        suggestions.appendChild(d);
    });
};

async function load() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await res.json();
    tbody.innerHTML = "";

    data.forEach(s => {
        const prev = lastPrices[s.symbol];
        let cls = "";

        if (prev !== undefined) {
            if (s.ltp > prev) cls = "blink-up";
            else if (s.ltp < prev) cls = "blink-down";
        }
        lastPrices[s.symbol] = s.ltp;

        const tv = s.symbol.replace("-EQ", "");

        tbody.innerHTML += `
        <tr onclick="window.open('https://www.tradingview.com/chart/?symbol=NSE:${tv}','_blank')">
            <td>${s.symbol}</td>
            <td>${s.company_name}</td>
            <td class="${cls}">${s.ltp.toFixed(2)}</td>
            <td class="${cls}">${s.pct.toFixed(2)}%</td>
            <td>${s.volume}</td>
            <td>${Number(s.open).toFixed(2)}</td>
            <td>${Number(s.high).toFixed(2)}</td>
            <td>${Number(s.low).toFixed(2)}</td>
            <td>${Number(s.close).toFixed(2)}</td>
            <td>
                <button onclick="event.stopPropagation(); removeStock('${s.symbol}')">✕</button>
            </td>
        </tr>`;
    });
}

async function removeStock(sym) {
    await fetch(`/remove?wid=${activeWatchlist}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: sym})
    });
    load();
}

function start() {
    if (timer) clearInterval(timer);
    load();
    timer = setInterval(load, 5000);
}

document.querySelector(".tab[data-id]").classList.add("active");
start();
