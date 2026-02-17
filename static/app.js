let wid = document.querySelector(".tab").dataset.id;
let rows = document.getElementById("rows");

document.querySelectorAll(".tab").forEach(t=>{
  t.onclick=()=>{wid=t.dataset.id;load();}
});

document.getElementById("addWL").onclick=async()=>{
  let n=prompt("Name"); if(!n) return;
  await fetch("/watchlist",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})});
  location.reload();
};

async function load(){
  let r=await fetch(`/prices?wid=${wid}`); let d=await r.json();
  rows.innerHTML="";
  d.forEach(x=>{
    rows.innerHTML+=`
    <tr onclick="chart('${x.symbol}')">
      <td>${x.symbol}</td>
      <td>${x.name}</td>
      <td>${x.ltp.toFixed(2)}</td>
      <td>${x.pct.toFixed(2)}%</td>
      <td><button onclick="event.stopPropagation();del(${x.id})">✕</button></td>
    </tr>`;
  });
}
load(); setInterval(load,5000);

async function del(id){
  await fetch("/remove",{method:"POST",headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  load();
}

function chart(sym){
  window.open(`https://www.tradingview.com/chart/?symbol=NSE:${sym.replace("-EQ","")}`,"_blank");
}

search.oninput=async()=>{
  suggestions.innerHTML="";
  if(!search.value) return;
  let r=await fetch(`/search?q=${search.value}`); let d=await r.json();
  d.forEach(s=>{
    let div=document.createElement("div");
    div.innerText=s.display_name;
    div.onclick=async()=>{
      await fetch(`/add?wid=${wid}`,{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(s)
      });
      suggestions.innerHTML=""; search.value=""; load();
    };
    suggestions.appendChild(div);
  });
};
