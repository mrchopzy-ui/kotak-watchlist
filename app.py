<!DOCTYPE html>
<html>
<head>
    <title>Nexus Asset Management</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>

<header class="top-bar">
    <h1>Nexus Asset Management</h1>
</header>

<div class="tabs">
    {% for w in watchlists %}
        <button class="tab" data-id="{{ w[0] }}">{{ w[1] }}</button>
    {% endfor %}
    <button class="tab add" id="addWatchlist">+</button>
</div>

<div class="search-box">
    <input id="search" placeholder="Type stock symbol">
    <div id="suggestions"></div>
</div>

<table>
    <thead>
        <tr>
            <th>Symbol</th>
            <th>Company Name</th>
            <th>LTP</th>
            <th>%</th>
            <th>Volume</th>
            <th>Open</th>
            <th>High</th>
            <th>Low</th>
            <th>Close</th>
            <th>Delete</th>
        </tr>
    </thead>
    <tbody id="watchlist"></tbody>
</table>

<script src="/static/app.js"></script>
</body>
</html>
