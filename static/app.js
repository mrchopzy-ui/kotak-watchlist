<!DOCTYPE html>
<html>
<head>
    <title>Nexus Asset Management</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>

<header class="top-bar">
    <h1>Nexus Asset Management</h1>
    <div class="indices" id="indices"></div>
</header>

<div class="tabs">
    {% for t in tabs %}
        <button class="tab {% if t == active %}active{% endif %}">
            {{ t }}
        </button>
    {% endfor %}
    <button class="tab add">+</button>
</div>

<div class="search-box">
    <input
        id="search"
        placeholder="Search stock symbol (e.g. ITC)"
        autocomplete="off"
    >
    <div id="suggestions"></div>
</div>

<table>
    <thead>
        <tr>
            <th>Symbol</th>
            <th>Company</th>
            <th>LTP</th>
            <th>%</th>
            <th>Volume</th>
            <th>O</th>
            <th>H</th>
            <th>L</th>
            <th>C</th>
            <th>Delete</th>
        </tr>
    </thead>
    <tbody id="watchlist"></tbody>
</table>

<script src="/static/app.js"></script>
</body>
</html>
