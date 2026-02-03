const tabsDiv = document.getElementById("tabs");
const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");

let activeWatchlist = null;
let priceTimer = null;

/* -------- RENDER TABS -------- */
function renderTabs(tabs) {
    tabsDiv.innerHTML = "";

    tabs.forEach(w => {
        const b = document.createElement("button");
        b.className = "tab";
        b.dataset.id = w[0];
        b.innerText = w[1];

        b.onclick = () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            b.classList.add("active");
            activeWatchlist = w[0];
            startPriceRefresh();
        };

        b.ondblclick = async () => {
            const name = prompt("Rename watchlist:", w[1]);
            if (!name) return;

            const res = await fetch(`/watchlist/${w[0]}`, {
                method: "PUT",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({name})
            });

            renderTabs(await res.json());
        };

        tabsDiv.appendChild(b);
    });

    const add = document.createElement("button");
    add.className = "tab add";
    add.innerText = "+";
    add.onclick = async () => {
        const name = prompt("New watchlist name:");
        if (!name) return;

        const res = await fetch("/watchlist", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name})
        });

        renderTabs(await res.json());
    };

    tabsDiv.appendChild(add);

    if (!activeWatchlist && tabs.length) {
        activeWatchlist = tabs[0][0];
    }

    document.querySelector(`[data-id="${activeWatchlist}"]`)?.classList.add("active");
}

/* -------- SEARCH -------- */
search.addEventListener("input", async () => {
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
            loadPrices();
        };
        suggestions.appendChild(d);
    });
});

/* -------- PRICES -------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${activeWatchlist}`);
    const data = await res.json();

    tbody.innerHTML = "";
    data.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td>${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td>${s.pct.toFixed(2)}%</td>
            <td>${s.volume}</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td><button onclick="removeStock('${s.symbol}')">✕</button></td>
        </tr>`;
    });
}

async function removeStock(sym) {
    await fetch(`/remove?wid=${activeWatchlist}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: sym})
    });
    loadPrices();
}

/* -------- AUTO REFRESH -------- */
function startPriceRefresh() {
    if (priceTimer) clearInterval(priceTimer);
    loadPrices();
    priceTimer = setInterval(loadPrices, 5000);
}

/* -------- INIT -------- */
fetch("/")
    .then(() => fetch("/watchlist", {method: "POST", body: JSON.stringify({name: "__noop__"})}))
    .catch(() => {});

fetch("/").then(() => location.reload());
