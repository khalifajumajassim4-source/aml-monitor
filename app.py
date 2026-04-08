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
    <title>AML Monitor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f3f6fb;
            color: #1f2937;
        }

        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 240px;
            height: 100vh;
            background: #0f172a;
            color: white;
            padding: 24px 18px;
        }

        .brand {
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 30px;
        }

        .nav-item {
            padding: 12px 14px;
            border-radius: 10px;
            margin-bottom: 10px;
            background: rgba(255,255,255,0.04);
        }

        .main {
            margin-left: 240px;
            min-height: 100vh;
        }

        .topbar {
            background: white;
            padding: 18px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e5e7eb;
        }

        .page {
            padding: 24px;
        }

        .metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
            margin-bottom: 20px;
        }

        .metric-card h3 {
            margin: 0 0 8px 0;
            font-size: 14px;
            color: #6b7280;
            font-weight: 600;
        }

        .metric-card p {
            margin: 0;
            font-size: 30px;
            font-weight: bold;
            color: #111827;
        }

        .section-title {
            margin: 0 0 16px 0;
            font-size: 20px;
            font-weight: bold;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px 18px;
        }

        label {
            display: block;
            font-size: 13px;
            margin-bottom: 6px;
            color: #4b5563;
            font-weight: 600;
        }

        input, select {
            width: 100%;
            padding: 11px 12px;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            background: #fff;
            font-size: 14px;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
        }

        .btn {
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
        }

        .btn-primary {
            background: #2563eb;
            color: white;
        }

        .btn-warning {
            background: #f59e0b;
            color: white;
        }

        .btn-danger {
            background: #dc2626;
            color: white;
        }

        .btn-success {
            background: #16a34a;
            color: white;
        }

        .btn-neutral {
            background: #6b7280;
            color: white;
        }

        .btn-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            overflow: hidden;
        }

        th, td {
            padding: 12px 10px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
            vertical-align: top;
            font-size: 14px;
        }

        th {
            background: #f8fafc;
            color: #374151;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }

        .badge {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
        }

        .badge-open {
            background: #dbeafe;
            color: #1d4ed8;
        }

        .badge-review {
            background: #fef3c7;
            color: #92400e;
        }

        .badge-escalated {
            background: #fee2e2;
            color: #b91c1c;
        }

        .badge-dismissed {
            background: #e5e7eb;
            color: #374151;
        }

        .badge-closed {
            background: #dcfce7;
            color: #166534;
        }

        .login-wrap {
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            background: linear-gradient(135deg, #0f172a, #1d4ed8);
        }

        .login-card {
            width: 100%;
            max-width: 420px;
            background: white;
            padding: 28px;
            border-radius: 18px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.2);
        }

        .login-card h2 {
            margin-top: 0;
            margin-bottom: 18px;
        }

        .muted {
            color: #6b7280;
            font-size: 13px;
        }

        .small-actions form {
            display: inline-block;
            margin: 3px;
        }

        .chart-box {
            height: 320px;
        }

        @media (max-width: 1100px) {
            .metrics {
                grid-template-columns: 1fr 1fr;
            }
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 800px) {
            .sidebar {
                display: none;
            }
            .main {
                margin-left: 0;
            }
            .metrics {
                grid-template-columns: 1fr;
            }
            .form-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
{% if not logged_in %}
    <div class="login-wrap">
        <div class="login-card">
            <h2>AML Monitor Login</h2>
            <form method="post" action="/login">
                <label>Username</label>
                <input name="username" required>

                <label>Password</label>
                <input name="password" type="password" required>

                <div style="margin-top:16px;">
                    <button class="btn btn-primary" type="submit">Login</button>
                </div>
            </form>
            <p class="muted" style="margin-top:14px;">Demo login: admin / admin123</p>
        </div>
    </div>
{% else %}
    <div class="sidebar">
        <div class="brand">AML Monitor</div>
        <div class="nav-item">Dashboard</div>
        <div class="nav-item">Transactions</div>
        <div class="nav-item">Alerts</div>
        <div class="nav-item">Case Review</div>
    </div>

    <div class="main">
        <div class="topbar">
            <div>
                <div style="font-size:22px;font-weight:bold;">Bank AML Dashboard</div>
                <div class="muted">Live transaction monitoring and suspicious activity review</div>
            </div>
            <div>
                <a href="/logout" style="text-decoration:none;">
                    <button class="btn btn-neutral">Logout</button>
                </a>
            </div>
        </div>

        <div class="page">
            <div class="metrics">
                <div class="card metric-card">
                    <h3>Total Alerts</h3>
                    <p>{{ alerts|length }}</p>
                </div>
                <div class="card metric-card">
                    <h3>Open Alerts</h3>
                    <p>{{ open_count }}</p>
                </div>
                <div class="card metric-card">
                    <h3>Escalated Alerts</h3>
                    <p>{{ escalated_count }}</p>
                </div>
                <div class="card metric-card">
                    <h3>Recent Transactions</h3>
                    <p>{{ transactions|length }}</p>
                </div>
            </div>

            <div class="grid-2">
                <div>
                    <div class="card">
                        <h2 class="section-title">Add Transaction</h2>
                        <form action="/add-transaction" method="post">
                            <div class="form-grid">
                                <div>
                                    <label>Account ID</label>
                                    <input type="number" name="account_id" required>
                                </div>
                                <div>
                                    <label>Amount</label>
                                    <input type="number" step="0.01" name="amount" required>
                                </div>

                                <div>
                                    <label>Currency</label>
                                    <input type="text" name="currency" value="USD" required>
                                </div>
                                <div>
                                    <label>Direction</label>
                                    <select name="direction" required>
                                        <option value="in">in</option>
                                        <option value="out">out</option>
                                    </select>
                                </div>

                                <div>
                                    <label>Channel</label>
                                    <input type="text" name="channel" value="branch">
                                </div>
                                <div>
                                    <label>Is Cash?</label>
                                    <select name="is_cash">
                                        <option value="true">true</option>
                                        <option value="false">false</option>
                                    </select>
                                </div>

                                <div>
                                    <label>Is International?</label>
                                    <select name="is_international">
                                        <option value="false">false</option>
                                        <option value="true">true</option>
                                    </select>
                                </div>
                                <div>
                                    <label>Counterparty ID</label>
                                    <input type="text" name="counterparty_id">
                                </div>

                                <div>
                                    <label>Counterparty Country</label>
                                    <input type="text" name="counterparty_country" value="US">
                                </div>
                                <div>
                                    <label>Balance After</label>
                                    <input type="number" step="0.01" name="balance_after">
                                </div>
                            </div>

                            <div style="margin-top:14px;">
                                <button class="btn btn-primary" type="submit">Save Transaction</button>
                            </div>
                        </form>
                    </div>

                    <div class="card">
                        <h2 class="section-title">Recent Transactions</h2>
                        <table>
                            <tr>
                                <th>ID</th>
                                <th>Account</th>
                                <th>Amount</th>
                                <th>Direction</th>
                                <th>Cash</th>
                                <th>Intl</th>
                                <th>Country</th>
                                <th>Time</th>
                            </tr>
                            {% for txn in transactions %}
                            <tr>
                                <td>{{ txn.id }}</td>
                                <td>{{ txn.account_id }}</td>
                                <td>{{ txn.amount }}</td>
                                <td>{{ txn.direction }}</td>
                                <td>{{ txn.is_cash }}</td>
                                <td>{{ txn.is_international }}</td>
                                <td>{{ txn.counterparty_country }}</td>
                                <td>{{ txn.occurred_at }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                </div>

                <div>
                    <div class="card">
                        <h2 class="section-title">Actions</h2>
                        <div class="btn-row">
                            <form action="/run-scan" method="post">
                                <button class="btn btn-primary" type="submit">Run AML Scan</button>
                            </form>
                        </div>

                        <div style="margin-top:18px;">
                            <form action="/upload-csv" method="post" enctype="multipart/form-data">
                                <label>Upload Transactions CSV</label>
                                <input type="file" name="file" required>
                                <button class="btn btn-success" type="submit">Upload CSV</button>
                            </form>
                        </div>

                        <p class="muted" style="margin-top:14px;">
                            CSV columns: account_id, amount, currency, direction, channel, is_cash,
                            is_international, counterparty_id, counterparty_country, balance_after
                        </p>
                    </div>

                    <div class="card">
                        <h2 class="section-title">Risk Score Overview</h2>
                        <div class="chart-box">
                            <canvas id="alertChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2 class="section-title">Alerts</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Account</th>
                        <th>Risk Score</th>
                        <th>Rules</th>
                        <th>Reason</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                    {% for alert in alerts %}
                    <tr>
                        <td>{{ alert.id }}</td>
                        <td>{{ alert.account_id }}</td>
                        <td><strong>{{ alert.risk_score }}</strong></td>
                        <td>{{ alert.rules_triggered }}</td>
                        <td>{{ alert.reason }}</td>
                        <td>
                            {% if alert.status == "open" %}
                                <span class="badge badge-open">{{ alert.status }}</span>
                            {% elif alert.status == "in_review" %}
                                <span class="badge badge-review">{{ alert.status }}</span>
                            {% elif alert.status == "escalated" %}
                                <span class="badge badge-escalated">{{ alert.status }}</span>
                            {% elif alert.status == "dismissed" %}
                                <span class="badge badge-dismissed">{{ alert.status }}</span>
                            {% else %}
                                <span class="badge badge-closed">{{ alert.status }}</span>
                            {% endif %}
                        </td>
                        <td class="small-actions">
                            <form action="/update-alert/{{ alert.id }}" method="post">
                                <input type="hidden" name="status" value="in_review">
                                <button class="btn btn-warning" type="submit">Review</button>
                            </form>

                            <form action="/update-alert/{{ alert.id }}" method="post">
                                <input type="hidden" name="status" value="escalated">
                                <button class="btn btn-danger" type="submit">Escalate</button>
                            </form>

                            <form action="/update-alert/{{ alert.id }}" method="post">
                                <input type="hidden" name="status" value="dismissed">
                                <button class="btn btn-neutral" type="submit">Dismiss</button>
                            </form>

                            <form action="/update-alert/{{ alert.id }}" method="post">
                                <input type="hidden" name="status" value="closed">
                                <button class="btn btn-success" type="submit">Close</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>

    <script>
        const labels = [{% for alert in alerts %}"Alert {{ alert.id }}",{% endfor %}];
        const data = [{% for alert in alerts %}{{ alert.risk_score }},{% endfor %}];

        new Chart(document.getElementById("alertChart"), {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Risk Score",
                    data: data
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    </script>
{% endif %}
</body>
</html>
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

    return render_template_string(
        HTML,
        logged_in=True,
        alerts=alerts,
        transactions=transactions,
        open_count=open_count,
        escalated_count=escalated_count,
    )

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
    db.commit()
    db.close()
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

    db.commit()
    db.close()
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
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
