const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
let active = document.querySelector(".tab").dataset.id;
let timer;

document.querySelectorAll(".tab").forEach(t=>{
    t.onclick=()=>{
        document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
        t.classList.add("active");
        active=t.dataset.id;
        refresh();
    }
});

search.oninput = async ()=>{
    suggestions.innerHTML="";
    if(!search.value) return;
    const r=await fetch(`/search?q=${search.value}`);
    const d=await r.json();
    d.forEach(s=>{
        const x=document.createElement("div");
        x.innerText=s.trading_symbol;
        x.onclick=async()=>{
            await fetch(`/add?wid=${active}`,{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify(s)
            });
            search.value="";
            suggestions.innerHTML="";
            refresh();
        };
        suggestions.appendChild(x);
    });
};

async function refresh(){
    const r=await fetch(`/prices?wid=${active}`);
    const d=await r.json();
    tbody.innerHTML="";
    d.forEach(s=>{
        tbody.innerHTML+=`
        <tr onclick="window.open('https://www.tradingview.com/chart/?symbol=NSE:${s.symbol.replace('-EQ','')}','_blank')">
        <td>${s.symbol}</td>
        <td>${s.company}</td>
        <td>${s.ltp.toFixed(2)}</td>
        <td>${s.pct.toFixed(2)}%</td>
        <td>${s.volume}</td>
        <td>${s.open}</td>
        <td>${s.high}</td>
        <td>${s.low}</td>
        <td>${s.close}</td>
        <td><button onclick="event.stopPropagation();removeStock('${s.symbol}')">✕</button></td>
        </tr>`;
    });
}

async function removeStock(sym){
    await fetch(`/remove?wid=${active}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({trading_symbol:sym})
    });
    refresh();
}

function start(){
    refresh();
    timer=setInterval(refresh,5000);
}

start();
