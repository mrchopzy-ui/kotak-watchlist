const list = document.getElementById("stockList");
const input = document.getElementById("stockInput");

async function loadStocks() {
  const res = await fetch("/api/stocks");
  const data = await res.json();

  list.innerHTML = "";

  data.forEach(stock => {
    const li = document.createElement("li");

    li.innerHTML = `
      <strong>${stock.symbol}</strong>
      — ₹${stock.price}
      (${stock.change}%)
      Vol: ${stock.volume}
      <button onclick="removeStock('${stock.symbol}')">Remove</button>
    `;

    list.appendChild(li);
  });
}

async function addStock() {
  const value = input.value.trim().toUpperCase();
  if (!value) return;

  await fetch(`/api/add/${value}`);
  input.value = "";
  loadStocks();
}

async function removeStock(symbol) {
  await fetch(`/api/remove/${symbol}`);
  loadStocks();
}

loadStocks();
setInterval(loadStocks, 30000); // refresh every 30 sec
