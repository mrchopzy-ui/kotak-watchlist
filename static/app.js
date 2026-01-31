async function loadPrices() {
    const res = await fetch("/prices");
    const data = await res.json();
    const tbody = document.getElementById("watchlist");
    tbody.innerHTML = "";

    data.forEach(s => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${s.symbol}</td>
            <td>${s.company}</td>
            <td class="${s.supertrend === 'Buy' ? 'green' : 'red'}">
                ${s.supertrend}
            </td>
            <td><button onclick="removeStock('${s.symbol}')">✕</button></td>
        `;
        tbody.appendChild(tr);
    });
}

setInterval(loadPrices, 300000); // 5 minutes
loadPrices();
