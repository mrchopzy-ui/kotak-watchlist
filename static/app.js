search.oninput = async () => {
    suggestions.innerHTML = "";
    if (!search.value) return;

    const res = await fetch(`/search?q=${search.value}`);
    const data = await res.json();

    data.forEach(s => {
        const d = document.createElement("div");
        d.className = "suggestion-item";
        d.innerHTML = `<strong>${s.symbol}</strong> — ${s.company}`;
        d.onclick = async () => {
            await fetch(`/add?wid=${activeWatchlist}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(s)
            });
            search.value = "";
            suggestions.innerHTML = "";
            load();
        };
        suggestions.appendChild(d);
    });
};
