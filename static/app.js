let active = document.querySelector(".tab");
let wid = active?.dataset.id;

function tv(symbol){
    const s = symbol.replace("-EQ","");
    window.open(`https://www.tradingview.com/chart/?symbol=NSE:${s}`);
}

async function load(){
    if(!wid) return;
    const r = await fetch(`/prices?wid=${wid}`);
    const d = await r.json();
    const t = document.getElementById("rows");
    t.innerHTML="";
    d.forEach(x=>{
        t.innerHTML+=`
        <tr onclick="tv('${x.symbol}')">
        <td>${x.symbol}</td>
        <td>${x.company}</td>
        <td>${x.ltp.toFixed(2)}</td>
        <td>${x.pct.toFixed(2)}%</td>
        <td>${x.volume}</td>
        <td>${x.open}</td>
        <td>${x.high}</td>
        <td>${x.low}</td>
        <td>${x.close}</td>
        <td><button onclick="event.stopPropagation();del('${x.symbol}')">✕</button></td>
        </tr>`;
    })
}

async function del(sym){
    await fetch("/remove",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({wid,symbol:sym})});
    load();
}

document.querySelectorAll(".tab").forEach(t=>{
    t.onclick=()=>{
        document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
        t.classList.add("active");
        wid=t.dataset.id;
        load();
    }
})

setInterval(load,5000);
load();
