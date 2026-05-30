import os
import csv
import io
import subprocess
import sys
from datetime import datetime
from decimal import Decimal

from flask import Flask, render_template_string, redirect, url_for, request, session
from db import SessionLocal, AMLAlert, Transaction, init_db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
init_db()

HTML = """
<!doctype html>
<html>
<head>
    <title>SentinelAML</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; font-family: Arial, sans-serif; background: #eef2f7; color: #172033; }
        a { text-decoration: none; }
        .login-wrap { min-height: 100vh; display: flex; justify-content: center; align-items: center; background: linear-gradient(135deg,#08111f,#123b7a); padding: 20px; }
        .login-card { width: 100%; max-width: 420px; background: white; border-radius: 20px; padding: 30px; box-shadow: 0 24px 70px rgba(0,0,0,.28); }
        .muted { color: #6b7280; font-size: 13px; }
        .shell { display: flex; min-height: 100vh; }
        .sidebar { width: 270px; background: #091221; color: white; padding: 24px 18px; position: fixed; top: 0; left: 0; bottom: 0; }
        .brand { font-size: 24px; font-weight: 800; margin-bottom: 6px; }
        .brand-sub { color: #9ca3af; font-size: 12px; margin-bottom: 26px; }
        .nav a { display: block; color: #d1d5db; padding: 13px 14px; border-radius: 12px; margin-bottom: 8px; font-weight: 700; }
        .nav a.active, .nav a:hover { background: #1d4ed8; color: white; }
        .sidebar-footer { position: absolute; bottom: 20px; left: 18px; right: 18px; color: #9ca3af; font-size: 12px; }
        .main { margin-left: 270px; width: calc(100% - 270px); min-height: 100vh; }
        .topbar { background: white; padding: 18px 28px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e5e7eb; position: sticky; top: 0; z-index: 5; }
        .page { padding: 24px; }
        .page-title { font-size: 24px; font-weight: 800; margin-bottom: 4px; }
        .metrics { display: grid; grid-template-columns: repeat(4, minmax(160px,1fr)); gap: 16px; margin-bottom: 20px; }
        .card { background: white; border-radius: 18px; padding: 20px; box-shadow: 0 8px 25px rgba(15,23,42,.06); margin-bottom: 20px; }
        .metric h3 { color: #6b7280; font-size: 13px; margin: 0 0 8px; text-transform: uppercase; letter-spacing: .04em; }
        .metric p { margin: 0; font-size: 30px; font-weight: 800; }
        .grid-2 { display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
        label { display: block; font-size: 13px; font-weight: 700; margin-bottom: 6px; color: #374151; }
        input, select { width: 100%; padding: 11px 12px; border: 1px solid #d1d5db; border-radius: 10px; background: white; font-size: 14px; }
        .btn { border: 0; border-radius: 10px; padding: 10px 15px; font-weight: 800; cursor: pointer; font-size: 14px; margin: 3px; }
        .btn-primary { background: #2563eb; color: white; }
        .btn-danger { background: #dc2626; color: white; }
        .btn-success { background: #16a34a; color: white; }
        .btn-warning { background: #f59e0b; color: #111827; }
        .btn-neutral { background: #6b7280; color: white; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 12px 10px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; font-size: 14px; }
        th { background: #f8fafc; color: #374151; text-transform: uppercase; letter-spacing: .03em; font-size: 12px; }
        .reason-cell { max-width: 440px; }
        .badge { display: inline-block; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
        .badge-open { background: #dbeafe; color: #1d4ed8; }
        .badge-review { background: #fef3c7; color: #92400e; }
        .badge-escalated { background: #fee2e2; color: #b91c1c; }
        .badge-dismissed { background: #e5e7eb; color: #374151; }
        .badge-closed { background: #dcfce7; color: #166534; }
        .chart-box { height: 310px; }
        .action-row { display: flex; gap: 10px; flex-wrap: wrap; }
        .notice { background: #eff6ff; color: #1e3a8a; border-left: 5px solid #2563eb; padding: 14px 16px; border-radius: 12px; margin-bottom: 20px; }
        @media (max-width: 950px) { .sidebar { display:none; } .main { margin-left:0; width:100%; } .metrics { grid-template-columns:1fr 1fr; } .grid-2 { grid-template-columns:1fr; } .form-grid { grid-template-columns:1fr; } }
    </style>
</head>
<body>
{% if not logged_in %}
    <div class="login-wrap">
        <div class="login-card">
            <h1>SentinelAML</h1>
            <p class="muted">Bank transaction monitoring and alert review platform</p>
            <form method="post" action="/login">
                <label>Username</label><input name="username" required>
                <label>Password</label><input name="password" type="password" required>
                <div style="margin-top:16px;"><button class="btn btn-primary" type="submit">Login</button></div>
            </form>
            <p class="muted">Demo login: admin / admin123</p>
        </div>
    </div>
{% else %}
<div class="shell">
    <aside class="sidebar">
        <div class="brand">SentinelAML</div>
        <div class="brand-sub">Compliance Monitoring Console</div>
        <nav class="nav">
            <a class="{{ 'active' if page == 'dashboard' else '' }}" href="{{ url_for('home') }}">Dashboard</a>
            <a class="{{ 'active' if page == 'transactions' else '' }}" href="{{ url_for('transactions_page') }}">Transactions</a>
            <a class="{{ 'active' if page == 'alerts' else '' }}" href="{{ url_for('alerts_page') }}">Alerts & Cases</a>
            <a class="{{ 'active' if page == 'analytics' else '' }}" href="{{ url_for('analytics_page') }}">Analytics</a>
            <a class="{{ 'active' if page == 'settings' else '' }}" href="{{ url_for('settings_page') }}">Settings</a>
        </nav>
        <div class="sidebar-footer">Final Project Demo<br>Rule-based AML + AI Alert Agent</div>
    </aside>

    <main class="main">
        <div class="topbar">
            <div><div class="page-title">{{ title }}</div><div class="muted">{{ subtitle }}</div></div>
            <a href="/logout"><button class="btn btn-neutral">Logout</button></a>
        </div>

        <div class="page">
            {% if message %}<div class="notice">{{ message }}</div>{% endif %}

            {% if page == 'dashboard' %}
                <div class="metrics">
                    <div class="card metric"><h3>Total Alerts</h3><p>{{ total_alerts }}</p></div>
                    <div class="card metric"><h3>Open Alerts</h3><p>{{ open_count }}</p></div>
                    <div class="card metric"><h3>Escalated</h3><p>{{ escalated_count }}</p></div>
                    <div class="card metric"><h3>Transactions</h3><p>{{ total_transactions }}</p></div>
                </div>
                <div class="grid-2">
                    <div class="card">
                        <h2>Operations</h2>
                        <p class="muted">Run the scanner first, then run the AI agent to email alert reports.</p>
                        <div class="action-row">
                            <form action="/run-scan" method="post"><button class="btn btn-primary" type="submit">Run AML Scan</button></form>
                            <form action="/run-agent" method="post"><button class="btn btn-danger" type="submit">Run AI Alert Agent</button></form>
                        </div>
                    </div>
                    <div class="card"><h2>Risk Score Overview</h2><div class="chart-box"><canvas id="alertChart"></canvas></div></div>
                </div>
                <div class="card"><h2>Latest Alerts</h2>{{ alerts_table|safe }}</div>
            {% endif %}

            {% if page == 'transactions' %}
                <div class="grid-2">
                    <div class="card">
                        <h2>Add Transaction</h2>
                        <form action="/add-transaction" method="post">
                            <div class="form-grid">
                                <div><label>Account ID</label><input type="number" name="account_id" required></div>
                                <div><label>Amount</label><input type="number" step="0.01" name="amount" required></div>
                                <div><label>Currency</label><input type="text" name="currency" value="USD" required></div>
                                <div><label>Direction</label><select name="direction"><option value="in">in</option><option value="out">out</option></select></div>
                                <div><label>Channel</label><input type="text" name="channel" value="branch"></div>
                                <div><label>Is Cash?</label><select name="is_cash"><option value="true">true</option><option value="false">false</option></select></div>
                                <div><label>Is International?</label><select name="is_international"><option value="false">false</option><option value="true">true</option></select></div>
                                <div><label>Counterparty ID</label><input type="text" name="counterparty_id"></div>
                                <div><label>Counterparty Country</label><input type="text" name="counterparty_country" value="US"></div>
                                <div><label>Balance After</label><input type="number" step="0.01" name="balance_after"></div>
                            </div>
                            <div style="margin-top:14px;"><button class="btn btn-primary" type="submit">Save Transaction</button></div>
                        </form>
                    </div>
                    <div class="card">
                        <h2>Upload Statement CSV</h2>
                        <p class="muted">Required columns: account_id, amount, currency, direction, channel, is_cash, is_international, counterparty_id, counterparty_country, balance_after.</p>
                        <form action="/upload-csv" method="post" enctype="multipart/form-data">
                            <input type="file" name="file" required>
                            <button class="btn btn-success" type="submit">Upload CSV</button>
                        </form>
                    </div>
                </div>
                <div class="card"><h2>Recent Transactions</h2>{{ transactions_table|safe }}</div>
            {% endif %}

            {% if page == 'alerts' %}
                <div class="card"><h2>Alert Case Management</h2><p class="muted">Review, escalate, dismiss, or close generated AML cases.</p>{{ alerts_table|safe }}</div>
            {% endif %}

            {% if page == 'analytics' %}
                <div class="grid-2">
                    <div class="card"><h2>Alert Risk Scores</h2><div class="chart-box"><canvas id="alertChart"></canvas></div></div>
                    <div class="card"><h2>Status Summary</h2><div class="chart-box"><canvas id="statusChart"></canvas></div></div>
                </div>
                <div class="card">
                    <h2>Rule Explanation</h2>
                    <table>
                        <tr><th>Rule</th><th>Meaning</th></tr>
                        <tr><td>STRUCTURING</td><td>Multiple cash deposits just under reporting thresholds.</td></tr>
                        <tr><td>CTR_CASH</td><td>Same-day cash activity above the configured threshold.</td></tr>
                        <tr><td>VELOCITY</td><td>Too many transactions or too much value in a short period.</td></tr>
                        <tr><td>RAPID_FLOW</td><td>Incoming money quickly leaves the account.</td></tr>
                        <tr><td>FAN_OUT</td><td>One account sends money to many counterparties.</td></tr>
                        <tr><td>HIGH_RISK_GEO</td><td>Transactions involving configured high-risk countries.</td></tr>
                    </table>
                </div>
            {% endif %}

            {% if page == 'settings' %}
                <div class="card">
                    <h2>System Settings</h2>
                    <table>
                        <tr><th>Setting</th><th>Value</th></tr>
                        <tr><td>Alert Recipient</td><td>{{ alert_recipient }}</td></tr>
                        <tr><td>Risk Alert Threshold</td><td>{{ risk_threshold }}</td></tr>
                        <tr><td>Database</td><td>{{ database_url }}</td></tr>
                        <tr><td>Email SMTP Configured</td><td>{{ smtp_configured }}</td></tr>
                    </table>
                    <p class="muted">Change these in Render Environment Variables, not directly in the code.</p>
                </div>
            {% endif %}
        </div>
    </main>
</div>

<script>
const labels = [{% for alert in alerts %}"Alert {{ alert.id }}",{% endfor %}];
const data = [{% for alert in alerts %}{{ alert.risk_score }},{% endfor %}];

if (document.getElementById("alertChart")) {
    new Chart(document.getElementById("alertChart"), {
        type: "bar",
        data: { labels: labels, datasets: [{ label: "Risk Score", data: data }] },
        options: { responsive: true, maintainAspectRatio: false }
    });
}
if (document.getElementById("statusChart")) {
    new Chart(document.getElementById("statusChart"), {
        type: "doughnut",
        data: {
            labels: ["Open", "In Review", "Escalated", "Dismissed", "Closed"],
            datasets: [{ data: [{{ open_count }}, {{ review_count }}, {{ escalated_count }}, {{ dismissed_count }}, {{ closed_count }}] }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}
</script>
{% endif %}
</body>
</html>
"""

def require_login():
    return session.get("logged_in")

def get_stats():
    db = SessionLocal()
    alerts = db.query(AMLAlert).order_by(AMLAlert.id.desc()).all()
    transactions = db.query(Transaction).order_by(Transaction.id.desc()).limit(50).all()
    total_transactions = db.query(Transaction).count()
    stats = {
        "alerts": alerts,
        "transactions": transactions,
        "total_alerts": len(alerts),
        "total_transactions": total_transactions,
        "open_count": sum(1 for a in alerts if a.status == "open"),
        "review_count": sum(1 for a in alerts if a.status == "in_review"),
        "escalated_count": sum(1 for a in alerts if a.status == "escalated"),
        "dismissed_count": sum(1 for a in alerts if a.status == "dismissed"),
        "closed_count": sum(1 for a in alerts if a.status == "closed"),
    }
    db.close()
    return stats

def status_badge(status):
    status = status or "open"
    badge = {
        "open": "badge-open",
        "in_review": "badge-review",
        "escalated": "badge-escalated",
        "dismissed": "badge-dismissed",
        "closed": "badge-closed",
    }.get(status, "badge-open")
    return f'<span class="badge {badge}">{status}</span>'

def build_alerts_table(alerts):
    html = "<table><tr><th>ID</th><th>Account</th><th>Risk</th><th>Rules</th><th>Reason</th><th>Status</th><th>Actions</th></tr>"
    for a in alerts:
        html += f"""
        <tr>
            <td>{a.id}</td>
            <td>{a.account_id}</td>
            <td><strong>{a.risk_score}</strong></td>
            <td>{a.rules_triggered}</td>
            <td class="reason-cell">{a.reason}</td>
            <td>{status_badge(a.status)}</td>
            <td>
                <form action="/update-alert/{a.id}" method="post" style="display:inline;"><input type="hidden" name="status" value="in_review"><button class="btn btn-warning" type="submit">Review</button></form>
                <form action="/update-alert/{a.id}" method="post" style="display:inline;"><input type="hidden" name="status" value="escalated"><button class="btn btn-danger" type="submit">Escalate</button></form>
                <form action="/update-alert/{a.id}" method="post" style="display:inline;"><input type="hidden" name="status" value="dismissed"><button class="btn btn-neutral" type="submit">Dismiss</button></form>
                <form action="/update-alert/{a.id}" method="post" style="display:inline;"><input type="hidden" name="status" value="closed"><button class="btn btn-success" type="submit">Close</button></form>
            </td>
        </tr>"""
    html += "</table>"
    return html

def build_transactions_table(transactions):
    html = "<table><tr><th>ID</th><th>Account</th><th>Amount</th><th>Direction</th><th>Cash</th><th>Intl</th><th>Country</th><th>Time</th></tr>"
    for t in transactions:
        html += f"<tr><td>{t.id}</td><td>{t.account_id}</td><td>{t.amount}</td><td>{t.direction}</td><td>{t.is_cash}</td><td>{t.is_international}</td><td>{t.counterparty_country}</td><td>{t.occurred_at}</td></tr>"
    html += "</table>"
    return html

def render_page(page, title, subtitle, message=None):
    if not require_login():
        return render_template_string(HTML, logged_in=False)

    stats = get_stats()
    return render_template_string(
        HTML,
        logged_in=True,
        page=page,
        title=title,
        subtitle=subtitle,
        message=message,
        alerts_table=build_alerts_table(stats["alerts"]),
        transactions_table=build_transactions_table(stats["transactions"]),
        alert_recipient=os.getenv("ALERT_RECIPIENT", "banksamityforensic@gmail.com"),
        risk_threshold=os.getenv("RISK_ALERT_THRESHOLD", "30"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///test.db"),
        smtp_configured="Yes" if os.getenv("SMTP_USER") and os.getenv("SMTP_PASS") else "No",
        **stats,
    )

@app.route("/", methods=["GET"])
def home():
    return render_page("dashboard", "Dashboard", "Overview of AML activity, alert volume, and monitoring operations.")

@app.route("/transactions", methods=["GET"])
def transactions_page():
    return render_page("transactions", "Transactions", "Add transactions manually or upload statement CSV files.")

@app.route("/alerts", methods=["GET"])
def alerts_page():
    return render_page("alerts", "Alerts & Cases", "Review generated AML alerts and manage case status.")

@app.route("/analytics", methods=["GET"])
def analytics_page():
    return render_page("analytics", "Analytics", "Risk score charts, status summary, and rule explanations.")

@app.route("/settings", methods=["GET"])
def settings_page():
    return render_page("settings", "Settings", "Current system configuration and environment status.")

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
    try:
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
        db.commit()
        db.close()
        return redirect(url_for("transactions_page"))
    except Exception as e:
        print("ADD TRANSACTION ERROR:", e)
        return render_page("transactions", "Transactions", "Add transactions manually or upload CSV files.", f"Error adding transaction: {e}")

@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    if not require_login():
        return redirect(url_for("home"))
    file = request.files.get("file")
    if not file:
        return redirect(url_for("transactions_page"))
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        reader = csv.DictReader(stream)
        db = SessionLocal()
        count = 0
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
            count += 1
        db.commit()
        db.close()
        return render_page("transactions", "Transactions", "Add transactions manually or upload CSV files.", f"Imported {count} transactions successfully.")
    except Exception as e:
        print("CSV IMPORT ERROR:", e)
        return render_page("transactions", "Transactions", "Add transactions manually or upload CSV files.", f"CSV import error: {e}")

@app.route("/run-scan", methods=["POST"])
def run_scan():
    if not require_login():
        return redirect(url_for("home"))
    try:
        subprocess.run([sys.executable, "aml_monitor.py"], timeout=60)
        return render_page("dashboard", "Dashboard", "Overview of AML activity, alert volume, and monitoring operations.", "AML scan completed.")
    except Exception as e:
        print("SCAN ERROR:", e)
        return render_page("dashboard", "Dashboard", "Overview of AML activity, alert volume, and monitoring operations.", f"Scan error: {e}")

@app.route("/run-agent", methods=["POST"])
def run_agent():
    if not require_login():
        return redirect(url_for("home"))
    try:
        subprocess.run([sys.executable, "ai_agent.py"], timeout=60)
        return render_page("alerts", "Alerts & Cases", "Review generated AML alerts and manage case status.", "AI Alert Agent completed. Check email and alert status.")
    except Exception as e:
        print("AGENT ERROR:", e)
        return render_page("alerts", "Alerts & Cases", "Review generated AML alerts and manage case status.", f"Agent error: {e}")

@app.route("/update-alert/<int:alert_id>", methods=["POST"])
def update_alert(alert_id):
    if not require_login():
        return redirect(url_for("home"))
    db = SessionLocal()
    alert = db.query(AMLAlert).filter(AMLAlert.id == alert_id).first()
    if alert:
        alert.status = request.form["status"]
        db.commit()
    db.close()
    return redirect(url_for("alerts_page"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)

    
