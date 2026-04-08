import os, csv, io, subprocess, sys
from datetime import datetime
from decimal import Decimal
from flask import Flask, render_template_string, redirect, url_for, request, session
from db import SessionLocal, AMLAlert, Transaction, init_db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
init_db()

HTML = """
<!doctype html><html><head><title>AML Monitor Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f4f6f8;color:#222}.topbar{background:#0b1f3a;color:#fff;padding:18px 28px;display:flex;justify-content:space-between;align-items:center}.container{max-width:1200px;margin:24px auto;padding:0 20px}.card{background:#fff;padding:20px;border-radius:12px;margin-bottom:20px;box-shadow:0 2px 10px rgba(0,0,0,.08)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}input,select{width:100%;padding:10px;margin-top:6px;margin-bottom:12px;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}button{background:#0b5ed7;color:#fff;border:none;padding:10px 16px;border-radius:8px;cursor:pointer;font-weight:bold;margin-right:6px}.danger{background:#c82333}.warning{background:#e0a800;color:#222}.success{background:#218838}.muted{color:#666;font-size:14px}table{width:100%;border-collapse:collapse;background:#fff}th,td{border:1px solid #ddd;padding:10px;text-align:left;vertical-align:top}th{background:#eef2f7}.badge{padding:5px 10px;border-radius:999px;font-size:12px;font-weight:bold;display:inline-block}.badge-open{background:#dbeafe;color:#1d4ed8}.badge-review{background:#fef3c7;color:#92400e}.badge-escalated{background:#fee2e2;color:#b91c1c}.badge-dismissed{background:#e5e7eb;color:#374151}.badge-closed{background:#dcfce7;color:#166534}.row{display:flex;gap:10px;flex-wrap:wrap}.metric{flex:1;min-width:180px;background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.08)}.metric h3{margin:0 0 8px 0;font-size:14px;color:#666}.metric p{margin:0;font-size:28px;font-weight:bold}.login-box{max-width:400px;margin:100px auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08)}
</style></head><body>
{% if not logged_in %}
<div class="login-box"><h2>Bank AML Login</h2><form method="post" action="/login"><label>Username</label><input name="username" required><label>Password</label><input name="password" type="password" required><button type="submit">Login</button></form><p class="muted">Demo login: admin / admin123</p></div>
{% else %}
<div class="topbar"><h1>AML Monitor Dashboard</h1><div><span style="margin-right:16px;">Logged in</span><a href="/logout" style="color:white;">Logout</a></div></div>
<div class="container">
<div class="row" style="margin-bottom:20px;"><div class="metric"><h3>Total Alerts</h3><p>{{ alerts|length }}</p></div><div class="metric"><h3>Open Alerts</h3><p>{{ open_count }}</p></div><div class="metric"><h3>Escalated Alerts</h3><p>{{ escalated_count }}</p></div><div class="metric"><h3>Transactions Loaded</h3><p>{{ transactions|length }}</p></div></div>
<div class="card"><form action="/run-scan" method="post"><button type="submit">Run AML Scan</button></form></div>
<div class="card"><h2>Add Transaction</h2><form action="/add-transaction" method="post"><div class="grid"><div><label>Account ID</label><input type="number" name="account_id" required><label>Amount</label><input type="number" step="0.01" name="amount" required><label>Currency</label><input type="text" name="currency" value="USD" required><label>Direction</label><select name="direction" required><option value="in">in</option><option value="out">out</option></select><label>Channel</label><input type="text" name="channel" value="branch"></div><div><label>Is Cash?</label><select name="is_cash"><option value="true">true</option><option value="false">false</option></select><label>Is International?</label><select name="is_international"><option value="false">false</option><option value="true">true</option></select><label>Counterparty ID</label><input type="text" name="counterparty_id"><label>Counterparty Country</label><input type="text" name="counterparty_country" value="US"><label>Balance After</label><input type="number" step="0.01" name="balance_after"></div></div><button type="submit">Save Transaction</button></form></div>
<div class="card"><h2>Upload Transactions CSV</h2><form action="/upload-csv" method="post" enctype="multipart/form-data"><input type="file" name="file" required><button type="submit">Upload CSV</button></form><p class="muted">Columns: account_id, amount, currency, direction, channel, is_cash, is_international, counterparty_id, counterparty_country, balance_after</p></div>
<div class="card"><h2>Alert Scores</h2><canvas id="alertChart"></canvas></div>
<div class="card"><h2>Recent Transactions</h2><table><tr><th>ID</th><th>Account ID</th><th>Amount</th><th>Direction</th><th>Cash</th><th>International</th><th>Country</th><th>Time</th></tr>{% for txn in transactions %}<tr><td>{{ txn.id }}</td><td>{{ txn.account_id }}</td><td>{{ txn.amount }}</td><td>{{ txn.direction }}</td><td>{{ txn.is_cash }}</td><td>{{ txn.is_international }}</td><td>{{ txn.counterparty_country }}</td><td>{{ txn.occurred_at }}</td></tr>{% endfor %}</table></div>
<div class="card"><h2>Alerts</h2><table><tr><th>ID</th><th>Account ID</th><th>Risk Score</th><th>Rules Triggered</th><th>Reason</th><th>Status</th><th>Actions</th></tr>{% for alert in alerts %}<tr><td>{{ alert.id }}</td><td>{{ alert.account_id }}</td><td>{{ alert.risk_score }}</td><td>{{ alert.rules_triggered }}</td><td>{{ alert.reason }}</td><td>{% if alert.status == "open" %}<span class="badge badge-open">{{ alert.status }}</span>{% elif alert.status == "in_review" %}<span class="badge badge-review">{{ alert.status }}</span>{% elif alert.status == "escalated" %}<span class="badge badge-escalated">{{ alert.status }}</span>{% elif alert.status == "dismissed" %}<span class="badge badge-dismissed">{{ alert.status }}</span>{% else %}<span class="badge badge-closed">{{ alert.status }}</span>{% endif %}</td><td><form action="/update-alert/{{ alert.id }}" method="post" style="display:inline;"><input type="hidden" name="status" value="in_review"><button class="warning" type="submit">Review</button></form><form action="/update-alert/{{ alert.id }}" method="post" style="display:inline;"><input type="hidden" name="status" value="escalated"><button class="danger" type="submit">Escalate</button></form><form action="/update-alert/{{ alert.id }}" method="post" style="display:inline;"><input type="hidden" name="status" value="dismissed"><button type="submit">Dismiss</button></form><form action="/update-alert/{{ alert.id }}" method="post" style="display:inline;"><input type="hidden" name="status" value="closed"><button class="success" type="submit">Close</button></form></td></tr>{% endfor %}</table></div>
</div>
<script>const labels=[{% for alert in alerts %}"Alert {{ alert.id }}",{% endfor %}];const data=[{% for alert in alerts %}{{ alert.risk_score }},{% endfor %}];new Chart(document.getElementById("alertChart"),{type:"bar",data:{labels:labels,datasets:[{label:"Risk Score",data:data}]}});</script>
{% endif %}
</body></html>
"""

def require_login():
    return session.get("logged_in")

@app.route("/", methods=["GET"])
def home():
    if not require_login():
        return render_template_string(HTML, logged_in=False)
    db = SessionLocal()
    alerts = db.query(AMLAlert).order_by(AMLAlert.id.desc()).all()
    transactions = db.query(Transaction).order_by(Transaction.id.desc()).limit(20).all()
    open_count = sum(1 for a in alerts if a.status == "open")
    escalated_count = sum(1 for a in alerts if a.status == "escalated")
    db.close()
    return render_template_string(HTML, logged_in=True, alerts=alerts, transactions=transactions, open_count=open_count, escalated_count=escalated_count)

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("username") == "admin" and request.form.get("password") == "admin123":
        session["logged_in"] = True
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/add-transaction", methods=["POST"])
def add_transaction():
    if not require_login():
        return redirect(url_for("home"))
    db = SessionLocal()
    db.add(Transaction(
        account_id=int(request.form["account_id"]),
        amount=Decimal(request.form["amount"]),
        currency=request.form["currency"],
        direction=request.form["direction"],
        channel=request.form.get("channel", ""),
        is_cash=request.form["is_cash"] == "true",
        is_international=request.form["is_international"] == "true",
        counterparty_id=request.form.get("counterparty_id", ""),
        counterparty_country=request.form.get("counterparty_country", "").upper(),
        occurred_at=datetime.now(),
        balance_after=Decimal(request.form["balance_after"]) if request.form.get("balance_after") else None,
    ))
    db.commit(); db.close()
    return redirect(url_for("home"))

@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    if not require_login():
        return redirect(url_for("home"))
    file = request.files.get("file")
    if not file:
        return redirect(url_for("home"))
    stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
    reader = csv.DictReader(stream)
    db = SessionLocal()
    for row in reader:
        db.add(Transaction(
            account_id=int(row["account_id"]),
            amount=Decimal(row["amount"]),
            currency=row.get("currency", "USD"),
            direction=row.get("direction", "in"),
            channel=row.get("channel", "branch"),
            is_cash=str(row.get("is_cash", "false")).lower() == "true",
            is_international=str(row.get("is_international", "false")).lower() == "true",
            counterparty_id=row.get("counterparty_id", ""),
            counterparty_country=row.get("counterparty_country", "US").upper(),
            occurred_at=datetime.now(),
            balance_after=Decimal(row["balance_after"]) if row.get("balance_after") else None,
        ))
    db.commit(); db.close()
    return redirect(url_for("home"))

@app.route("/update-alert/<int:alert_id>", methods=["POST"])
def update_alert(alert_id):
    if not require_login():
        return redirect(url_for("home"))
    db = SessionLocal()
    alert = db.query(AMLAlert).filter_by(id=alert_id).first()
    if alert:
        alert.status = request.form["status"]
        db.commit()
    db.close()
    return redirect(url_for("home"))

@app.route("/run-scan", methods=["POST"])
def run_scan():
    if not require_login():
        return redirect(url_for("home"))
    subprocess.run([sys.executable, "aml_monitor.py"], timeout=60)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
