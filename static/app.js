let active = 1;
let timer = null;

function loadWatchlist(id) {
  active = id;
  fetchPrices();
}

function fetchPrices() {
  fetch(`/prices?wid=${active}`)
    .then(r => r.json())
    .then(d => {
      const tbody = document.getElementById("rows");
      tbody.innerHTML = "";
      d.forEach(s => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${s.symbol}</td>
          <td>${s.company}</td>
          <td>${s.price}</td>
          <td class="${s.pct >= 0 ? 'green' : 'red'}">${s.pct}%</td>
          <td>${s.volume}</td>
          <td>${s.open}</td>
          <td>${s.high}</td>
          <td>${s.low}</td>
          <td>${s.close}</td>
          <td><button onclick="removeStock('${s.symbol}')">✖</button></td>
        `;
        tr.onclick = () => window.open(`https://www.tradingview.com/symbols/NSE-${s.symbol.replace("-EQ","")}`, "_blank");
        tbody.appendChild(tr);
      });
    });
}

function removeStock(sym) {
  fetch(`/remove?wid=${active}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({trading_symbol: sym})
  }).then(fetchPrices);
}

document.getElementById("search").oninput = e => {
  fetch(`/search?q=${e.target.value}`)
    .then(r => r.json())
    .then(d => {
      const box = document.getElementById("suggestions");
      box.innerHTML = "";
      d.forEach(s => {
        const div = document.createElement("div");
        div.textContent = s.trading_symbol;
        div.onclick = () => {
          fetch(`/add?wid=${active}`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(s)
          }).then(fetchPrices);
          box.innerHTML = "";
          e.target.value = "";
        };
        box.appendChild(div);
      });
    });
};

timer = setInterval(fetchPrices, 5000);
fetchPrices();
