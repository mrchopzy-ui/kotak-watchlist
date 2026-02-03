const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addBtn = document.getElementById("addWatchlist");

let activeWatchlist = document.querySelector(".tab[data-id]").dataset.id;
let priceTimer = null;

/* ---------- ADD WATCHLIST ---------- */
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

/* ---------- TAB SWITCH & RENAME ---------- */
document.querySelectorAll(".tab[data-id]").forEach(tab => {
    tab.onclick = () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");

        activeWatchlist = tab.dataset.id;
        startPriceRefresh();
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

/* ---------- SEARCH ---------- */
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

/* ---------- LOAD PRICES ---------- */
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
            <td>
                <button onclick="removeStock('${s.symbol}')">✕</button>
            </td>
        </tr>`;
    });
}

/* ---------- AUTO REFRESH ---------- */
function startPriceRefresh() {
    if (priceTimer) {
        clearInterval(priceTimer);
    }

    loadPrices(); // immediate fetch

    priceTimer = setInterval(() => {
        loadPrices();
    }, 5000); // every 5 seconds
}

/* ---------- REMOVE STOCK ---------- */
async function removeStock(sym) {
    await fetch(`/remove?wid=${activeWatchlist}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: sym})
    });

    loadPrices();
}

/* ---------- INIT ---------- */
document.querySelector(".tab[data-id]").classList.add("active");
startPriceRefresh();
