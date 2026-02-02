let sortColumn = null;
let sortAsc = true;
let lastData = [];

const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");

/* ---------- WATCHLIST RENAME ---------- */
function editTab(btn, oldName) {
    const input = document.createElement("input");
    input.value = oldName;
    input.className = "tab-edit";

    input.onkeydown = async (e) => {
        if (e.key === "Enter") {
            await fetch("/rename-tab", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({old: oldName, new: input.value})
            });
            location.reload();
        }
    };

    btn.replaceWith(input);
    input.focus();
}

/* ---------- SEARCH AUTO ADD ---------- */
search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(stock => {
        const div = document.createElement("div");
        div.className = "suggestion-item";
        div.innerHTML = `<strong>${stock.trading_symbol}</strong><br><small>${stock.company_name}</small>`;

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

/* ---------- TABS ---------- */
function switchTab(tab) {
    fetch("/set-tab", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tab})
    }).then(() => location.reload());
}

function createTab() {
    const name = prompt("Watchlist name:");
    if (!name) return;

    fetch("/new-tab", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    }).then(() => location.reload());
}

/* ---------- SORT ---------- */
function sortBy(col) {
    sortAsc = sortColumn === col ? !sortAsc : true;
    sortColumn = col;
    render();
}

/* ---------- DATA ---------- */
async function loadPrices() {
    const res = await fetch("/prices");
    lastData = await res.json();
    render();
}

function render() {
    let data = [...lastData];
    if (sortColumn) {
        data.sort((a,b) =>
            sortAsc ? a[sortColumn] > b[sortColumn] : a[sortColumn] < b[sortColumn]
        );
    }

    tbody.innerHTML = "";
    data.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td>${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp}</td>
            <td>${s.change_pct}%</td>
            <td>${s.open}</td>
            <td>${s.high}</td>
            <td>${s.low}</td>
            <td>${s.close}</td>
            <td><button class="delete" onclick="removeStock('${s.symbol}')">✕</button></td>
        </tr>`;
    });
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
