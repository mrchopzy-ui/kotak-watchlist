let activeWatchlist;
let timer;
let mode = "EQ";
let selectedFO = null;

document.querySelectorAll(".tab").forEach(t => {
    t.onclick = () => {
        document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
        t.classList.add("active");
        activeWatchlist = t.dataset.id;
        refresh();
    };
});
document.querySelector(".tab").click();

document.querySelectorAll(".inst").forEach(b => {
    b.onclick = () => {
        document.querySelectorAll(".inst").forEach(x => x.classList.remove("active"));
        b.classList.add("active");
        mode = b.dataset.type;
        toggle();
    };
});

function toggle(){
    eqBox.classList.add("hidden");
    indexBox.classList.add("hidden");
    foBox.classList.add("hidden");
    if(mode==="EQ") eqBox.classList.remove("hidden");
    if(mode==="INDEX") indexBox.classList.remove("hidden");
    if(mode==="FO") foBox.classList.remove("hidden");
}

/* -------- STOCK SEARCH -------- */
searchEQ.oninput = async () => {
    if(!searchEQ.value) return suggestEQ.innerHTML="";
    let r = await fetch(`/search?q=${searchEQ.value}`);
    let d = await r.json();
    suggestEQ.innerHTML="";
    d.forEach(s=>{
        let div=document.createElement("div");
        div.textContent=s.trading_symbol;
        div.onclick=()=>addEQ(s.trading_symbol);
        suggestEQ.appendChild(div);
    });
};

async function addEQ(sym){
    await fetch(`/add?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            symbol:sym,
            exchange:"nse_cm",
            instrument_type:"EQ"
        })
    });
    searchEQ.value="";
    suggestEQ.innerHTML="";
    refresh();
}

/* -------- INDEX SEARCH -------- */
searchIndex.oninput = ()=>{
    let q = searchIndex.value.toLowerCase();
    suggestIndex.innerHTML="";
    ["Nifty 50","Nifty Bank"].filter(x=>x.toLowerCase().includes(q)).forEach(i=>{
        let d=document.createElement("div");
        d.textContent=i;
        d.onclick=()=>addIndex(i);
        suggestIndex.appendChild(d);
    });
};

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

/* -------- F&O SEARCH -------- */
searchFO.oninput = async ()=>{
    if(!searchFO.value) return suggestFO.innerHTML="";
    let r = await fetch(`/search?q=${searchFO.value}`);
    let d = await r.json();
    suggestFO.innerHTML="";
    d.forEach(s=>{
        let div=document.createElement("div");
        div.textContent=s.trading_symbol;
        div.onclick=()=>{ selectedFO=s.trading_symbol; suggestFO.innerHTML=""; searchFO.value=s.trading_symbol; };
        suggestFO.appendChild(div);
    });
};

foType.onchange = ()=>{
    foStrike.classList.toggle("hidden", foType.value==="FUT");
    foCP.classList.toggle("hidden", foType.value==="FUT");
};

async function addFO(){
    if(!selectedFO) return alert("Select underlying first");
    let sym = selectedFO + foExpiry.value + (foType.value==="FUT"?"FUT":foStrike.value+foCP.value);
    await fetch(`/add?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            symbol:sym,
            exchange:"nse_fo",
            instrument_type:foType.value
        })
    });
    refresh();
}

/* -------- WATCHLIST -------- */
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
            <td><button onclick="event.stopPropagation();removeItem('${x.symbol}')">✕</button></td>
        </tr>`;
    });
}

function removeItem(sym){
    fetch(`/remove?wid=${activeWatchlist}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({trading_symbol:sym})
    }).then(load);
}

function chart(sym){
    window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym.replace("-EQ","")}`,"_blank");
}
