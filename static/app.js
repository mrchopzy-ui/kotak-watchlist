let wid = document.querySelector(".tab").dataset.id;
let timer;

function refresh(){
fetch(`/prices?wid=${wid}`).then(r=>r.json()).then(d=>{
    let t="";
    d.forEach(s=>{
        let sym=s.symbol.replace("-EQ","");
        t+=`
        <tr onclick="window.open('https://www.tradingview.com/chart/?symbol=NSE:${sym}')">
        <td>${s.symbol}</td>
        <td>${s.company}</td>
        <td>${s.ltp.toFixed(2)}</td>
        <td>${s.pct.toFixed(2)}%</td>
        <td>${s.type}</td>
        <td><button onclick="event.stopPropagation();del('${s.symbol}')">✕</button></td>
        </tr>`;
    });
    document.getElementById("watchlist").innerHTML=t;
});
}

function del(s){
fetch(`/remove?wid=${wid}`,{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({symbol:s})
}).then(refresh);
}

document.getElementById("search").oninput=async e=>{
let q=e.target.value;
if(!q)return;
let d=await fetch(`/search?q=${q}`).then(r=>r.json());
let s=document.getElementById("suggestions");
s.innerHTML="";
d.forEach(x=>{
let div=document.createElement("div");
div.innerText=`${x.symbol} (${x.type})`;
div.onclick=()=>{
fetch(`/add?wid=${wid}`,{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(x)
}).then(()=>{s.innerHTML="";refresh();});
};
s.appendChild(div);
});
};

setInterval(refresh,5000);
refresh();
