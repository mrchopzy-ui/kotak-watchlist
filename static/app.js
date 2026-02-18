let activeWatchlist;
let timer;
let mode = "EQ";

document.querySelectorAll(".tab").forEach(t=>{
    t.onclick=()=>{
        document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
        t.classList.add("active");
        activeWatchlist = t.dataset.id;
        refresh();
    };
});
document.querySelector(".tab").click();

document.querySelectorAll(".inst").forEach(b=>{
    b.onclick=()=>{
        document.querySelectorAll(".inst").forEach(x=>x.classList.remove("active"));
        b.classList.add("active");
        mode=b.dataset.type;
        toggleBoxes();
    };
});

function toggleBoxes(){
    ["eqBox","indexBox","foBox"].forEach(id=>document.getElementById(id).classList.add("hidden"));
    if(mode==="EQ") eqBox.classList.remove("hidden");
    if(mode==="INDEX") indexBox.classList.remove("hidden");
    if(mode==="FO") foBox.classList.remove("hidden");
}

search.oninput = async ()=>{
    if(!search.value) return suggestions.innerHTML="";
    let r = await fetch("/search?q="+search.value);
    let d = await r.json();
    suggestions.innerHTML="";
    d.forEach(s=>{
        let div=document.createElement("div");
        div.textContent=s.trading_symbol;
        div.onclick=()=>addStock(s);
        suggestions.appendChild(div);
    });
};

async function addStock(s){
    await fetch(`/add?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            symbol:s.trading_symbol,
            exchange:"nse_cm",
            instrument_type:"EQ"
        })
    });
    search.value="";
    suggestions.innerHTML="";
    refresh();
}

function addIndex(name){
    fetch(`/add?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            symbol:name,
            exchange:"nse_cm",
            instrument_type:"INDEX"
        })
    }).then(refresh);
}

async function addFO(){
    let u=foUnderlying.value;
    let e=foExpiry.value;
    let t=foType.value;
    let s=u+e+(t==="FUT"?"FUT":foStrike.value+foCP.value);
    await fetch(`/add?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            symbol:s,
            exchange:"nse_fo",
            instrument_type:t,
            expiry:e,
            strike:t==="OPT"?foStrike.value:null,
            option_type:t==="OPT"?foCP.value:null
        })
    });
    refresh();
}

async function refresh(){
    if(timer) clearInterval(timer);
    await load();
    timer=setInterval(load,5000);
}

async function load(){
    let r=await fetch(`/prices?wid=${activeWatchlist}`);
    let d=await r.json();
    watchlist.innerHTML="";
    d.forEach(x=>{
        watchlist.innerHTML+=`
        <tr onclick="chart('${x.symbol}')">
            <td>${x.symbol}</td>
            <td>${x.company}</td>
            <td>${x.ltp.toFixed(2)}</td>
            <td>${x.pct.toFixed(2)}%</td>
            <td>${x.volume}</td>
            <td>${x.open}</td>
            <td>${x.high}</td>
            <td>${x.low}</td>
            <td>${x.close}</td>
            <td><button onclick="event.stopPropagation();remove('${x.symbol}')">✕</button></td>
        </tr>`;
    });
}

function remove(sym){
    fetch(`/remove?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({trading_symbol:sym})
    }).then(load);
}

function chart(sym){
    window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym.replace("-EQ","")}`,"_blank");
}
