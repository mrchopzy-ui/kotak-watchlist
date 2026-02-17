const search = document.getElementById("search");
const suggestions = document.getElementById("suggestions");
const tbody = document.getElementById("watchlist");
const addWL = document.getElementById("addWatchlist");

let active = document.querySelector(".tab").dataset.id;

function load() {
    fetch(`/prices?wid=${active}`)
        .then(r => r.json())
        .then(d => {
            tbody.innerHTML = "";
            d.forEach(s => {
                const base = s.symbol.replace(/-EQ$/, "").replace(/\d+/g,"");
                tbody.innerHTML += `
                <tr onclick="window.open('https://www.tradingview.com/chart/?symbol=NSE:${base}','_blank')">
                    <td>${s.symbol}</td>
                    <td>${s.company}</td>
                    <td>${s.ltp.toFixed(2)}</td>
                    <td>${s.pct.toFixed(2)}%</td>
                    <td><button onclick="event.stopPropagation();remove('${s.symbol}')">✕</button></td>
                </tr>`;
            });
        });
}

function remove(sym){
    fetch(`/remove?wid=${active}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({symbol:sym})
    }).then(load);
}

search.oninput = () => {
    suggestions.innerHTML = "";
    if(!search.value) return;

    fetch(`/search?q=${search.value}`)
        .then(r=>r.json())
        .then(d=>{
            d.forEach(s=>{
                const div=document.createElement("div");
                div.className="suggestion";
                div.innerText = `${s.symbol} (${s.segment})`;
                div.onclick=()=>{
                    fetch(`/add?wid=${active}`,{
                        method:"POST",
                        headers:{"Content-Type":"application/json"},
                        body:JSON.stringify(s)
                    }).then(load);
                    suggestions.innerHTML="";
                    search.value="";
                };
                suggestions.appendChild(div);
            });
        });
};

document.querySelectorAll(".tab").forEach(t=>{
    t.onclick=()=>{
        document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
        t.classList.add("active");
        active=t.dataset.id;
        load();
    };
});

addWL.onclick=()=>{
    const n=prompt("Watchlist name");
    if(!n) return;
    fetch("/watchlist",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:n})})
        .then(()=>location.reload());
};

setInterval(load,5000);
load();
