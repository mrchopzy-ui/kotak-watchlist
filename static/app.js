let active=document.querySelector(".tab").dataset.id;
let timer=null;

document.querySelectorAll(".tab").forEach(t=>{
  t.onclick=()=>{
    document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
    t.classList.add("active");
    active=t.dataset.id;
    start();
  }
});

const search=document.getElementById("search");
const sug=document.getElementById("suggestions");

search.oninput=async()=>{
  sug.innerHTML="";
  if(!search.value)return;
  const r=await fetch(`/search?q=${search.value}`);
  const d=await r.json();
  d.forEach(s=>{
    const div=document.createElement("div");
    div.innerText=s.trading_symbol;
    div.onclick=async()=>{
      await fetch(`/add?wid=${active}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(s)
      });
      search.value="";
      sug.innerHTML="";
      load();
    };
    sug.appendChild(div);
  });
};

async function load(){
  const r=await fetch(`/prices?wid=${active}`);
  const d=await r.json();
  const tb=document.getElementById("watchlist");
  tb.innerHTML="";
  d.forEach(x=>{
    tb.innerHTML+=`
    <tr onclick="chart('${x.symbol}')">
      <td>${x.symbol}</td>
      <td>${x.company}</td>
      <td>${x.ltp.toFixed(2)}</td>
      <td>${x.pct.toFixed(2)}%</td>
      <td>${x.volume}</td>
      <td>${x.open}</td><td>${x.high}</td><td>${x.low}</td><td>${x.close}</td>
      <td><button onclick="event.stopPropagation();del('${x.exchange_segment}','${x.exchange_token}')">✕</button></td>
    </tr>`;
  });
}

async function del(seg,tok){
  await fetch(`/remove?wid=${active}`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({exchange_segment:seg,exchange_token:tok})
  });
  load();
}

function chart(sym){
  window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym.replace("-EQ","")}`,"_blank");
}

function start(){
  if(timer)clearInterval(timer);
  load();
  timer=setInterval(load,5000);
}

start();
