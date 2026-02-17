const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addWL = document.getElementById("addWatchlist");

let active = document.querySelector(".tab").dataset.id;

function loadPrices() {
    fetch(`/prices?wid=${active}`)
        .then(r => r.json())
        .then(d => {
            tbody.innerHTML = "";
            d.forEach(s => {
                tbody.innerHTML += `
                <tr>
                    <td>${s.symbol}</td>
                    <td>${s.company}</td>
                    <td>${s.ltp.toFixed(2)}</td>
                    <td>${s.pct.toFixed(2)}%</td>
                    <td><button onclick="removeStock('${s.symbol}')">✕</button></td>
                </tr>`;
            });
        });
}

function removeStock(sym){
    fetch(`/remove?wid=${active}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({symbol:sym})
    }).then(loadPrices);
}

search.oninput = async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(s => {
        const div = document.createElement("div");
        div.className = "suggestion";
        div.textContent = `${s.symbol} (${s.segment})`;
        div.onclick = async () => {
            await fetch(`/add?wid=${active}`, {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify(s)
            });
            search.value = "";
            suggestions.innerHTML = "";
            loadPrices();
        };
        suggestions.appendChild(div);
    });
};

document.querySelectorAll(".tab").forEach(t => {
    t.onclick = () => {
        document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        active = t.dataset.id;
        loadPrices();
    };
});

addWL.onclick = async () => {
    const name = prompt("Watchlist name");
    if (!name) return;
    await fetch("/watchlist", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({name})
    });
    location.reload();
};

setInterval(loadPrices, 5000);
loadPrices();
