let wid = 1;

function load(id) {
  wid = id;
  refresh();
}

function refresh() {
  fetch(`/prices?wid=${wid}`)
    .then(r => r.json())
    .then(d => {
      let t = "";
      d.forEach(x => {
        t += `<tr onclick="chart('${x.symbol}')">
          <td>${x.symbol}</td>
          <td>${x.company}</td>
          <td>${x.ltp.toFixed(2)}</td>
          <td class="${x.pct >= 0 ? 'up':'dn'}">${x.pct.toFixed(2)}%</td>
        </tr>`;
      });
      document.getElementById("rows").innerHTML = t;
    });
}

setInterval(refresh, 5000);

function chart(sym) {
  window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym}`);
}

const s = document.getElementById("search");
const box = document.getElementById("suggestions");

s.oninput = () => {
  if (s.value.length < 1) return box.innerHTML = "";
  fetch(`/search?q=${s.value}`)
    .then(r => r.json())
    .then(d => {
      box.innerHTML = d.map(x =>
        `<div onclick="add('${x.symbol}')">${x.symbol} - ${x.company}</div>`
      ).join("");
    });
};

function add(sym) {
  fetch(`/add?wid=${wid}`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({symbol:sym})
  }).then(()=> {
    s.value="";
    box.innerHTML="";
    refresh();
  });
}
