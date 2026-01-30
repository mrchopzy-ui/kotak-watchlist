let selectedStock = null;

const searchInput = document.getElementById("search");
const suggestionsDiv = document.getElementById("suggestions");
const addBtn = document.getElementById("addBtn");
const watchlistBody = document.getElementById("watchlist");

searchInput.addEventListener("input", async () => {
    const q = searchInput.value.trim();
    suggestionsDiv.innerHTML = "";
    selectedStock = null;
    addBtn.disabled = true;

    if (!q) return;

    const res = await fetch(`/search?q=${q}`);
    const data = await res.json();

    data.forEach(stock => {
        const div = document.createElement("div");
        div.textContent = stock.trading_symbol;
        div.onclick = () => {
            selectedStock = stock;
            searchInput.value = stock.trading_symbol;
            suggestionsDiv.innerHTML = "";
            addBtn.disabled = false;
        };
        suggestionsDiv.appendChild(div);
    });
});

addBtn.onclick = async () => {
    if (!selectedStock) {
        alert("Please select a stock from suggestions");
        return;
    }

    await fetch("/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(selectedStock)
    });

    selectedStock = null;
    searchInput.value = "";
    addBtn.disabled = true;
    loadWatchlist();
};

async function loadWatchlist() {
    const res = await fetch("/list");
    const data = await res.json();
    watchlistBody.innerHTML = "";

    data.forEach(stock => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${stock.trading_symbol}</td>
            <td>${stock.company_name}</td>
            <td><button onclick="removeStock('${stock.trading_symbol}')">❌</button></td>
        `;
        watchlistBody.appendChild(tr);
    });
}

async function removeStock(symbol) {
    await fetch("/remove", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({trading_symbol: symbol})
    });
    loadWatchlist();
}

loadWatchlist();
