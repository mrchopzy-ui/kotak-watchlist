const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addWL = document.getElementById("addWatchlist");

let active = document.querySelector(".tab").dataset.id;
let refreshTimer = null;

/* ---------- LOAD PRICES ---------- */
async function loadPrices() {
    const res = await fetch(`/prices?wid=${active}`);
    const data = await res.json();

    tbody.innerHTML = "";
    data.forEach(s => {
        tbody.innerHTML += `
        <tr>
            <td>${s.symbol}</td>
            <td>${s.company}</td>
            <td>${s.ltp.toFixed(2)}</td>
            <td>${s.pct.toFixed(2)}%</td>
            <td>
                <button onclick="removeStock('${s.symbol}')">✕</button>
            </td>
        </tr>`;
    });
}

/* ---------- REMOVE ---------- */
async function removeStock(sym) {
    await fetch(`/remove?wid=${active}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({symbol: sym})
    });
    loadPrices();
}

/* ---------- SEARCH ---------- */
search.addEventListener("input", async () => {
    suggestions.innerHTML = "";
    if (!search.value.trim()) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(s => {
        const div = document.createElement("div");
        div.className = "suggestion";
        div.textContent = `${s.symbol} (${s.segment})`;

        div.onclick = async () => {
            await fetch(`/add?wid=${active}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(s)
            });

            search.value = "";
            suggestions.innerHTML = "";
            await loadPrices(); // 🔑 WAIT FOR INSERT
        };

        suggestions.appendChild(div);
    });
});

/* ---------- TABS ---------- */
document.querySelectorAll(".tab").forEach(t => {
    t.onclick = () => {
        document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        active = t.dataset.id;
        loadPrices();
    };
});

/* ---------- ADD WATCHLIST ---------- */
addWL.onclick = async () => {
    const name = prompt("Watchlist name");
    if (!name) return;

    await fetch("/watchlist", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name})
    });

    location.reload();
};

/* ---------- AUTO REFRESH ---------- */
if (refreshTimer) clearInterval(refreshTimer);
refreshTimer = setInterval(loadPrices, 5000);
loadPrices();
