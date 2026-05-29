```python
def require_login():
    return session.get("logged_in")


@app.route("/", methods=["GET"])
def home():
    if not require_login():
        return render_template_string(HTML, logged_in=False)

    db = SessionLocal()

    alerts = db.query(AMLAlert).order_by(AMLAlert.id.desc()).all()

    transactions = (
        db.query(Transaction)
        .order_by(Transaction.id.desc())
        .limit(20)
        .all()
    )

    open_count = sum(1 for a in alerts if a.status == "open")
    review_count = sum(1 for a in alerts if a.status == "in_review")
    escalated_count = sum(1 for a in alerts if a.status == "escalated")

    db.close()

    return render_template_string(
        HTML,
        logged_in=True,
        alerts=alerts,
        transactions=transactions,
        open_count=open_count,
        review_count=review_count,
        escalated_count=escalated_count,
    )


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == "admin" and password == "admin123":
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

        txn = Transaction(
            account_id=int(request.form["account_id"]),
            amount=Decimal(request.form["amount"]),
            currency=request.form["currency"],
            direction=request.form["direction"],
            channel=request.form.get("channel", ""),
            is_cash=request.form["is_cash"] == "true",
            is_international=request.form["is_international"] == "true",
            counterparty_id=request.form.get("counterparty_id", ""),
            counterparty_country=request.form.get(
                "counterparty_country", ""
            ).upper(),
            occurred_at=datetime.now(),
            balance_after=Decimal(request.form["balance_after"])
            if request.form.get("balance_after")
            else None,
        )

        db.add(txn)
        db.commit()
        db.close()

    except Exception as e:
        print("ADD TRANSACTION ERROR:", e)

    return redirect(url_for("home"))


@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    if not require_login():
        return redirect(url_for("home"))

    file = request.files.get("file")

    if not file:
        return redirect(url_for("home"))

    try:
        stream = io.StringIO(
            file.stream.read().decode("utf-8"),
            newline=None,
        )

        reader = csv.DictReader(stream)

        db = SessionLocal()

        count = 0

        for row in reader:
            txn = Transaction(
                account_id=int(row["account_id"]),
                amount=Decimal(row["amount"]),
                currency=row.get("currency", "USD"),
                direction=row.get("direction", "in"),
                channel=row.get("channel", "branch"),
                is_cash=str(
                    row.get("is_cash", "false")
                ).lower() == "true",
                is_international=str(
                    row.get("is_international", "false")
                ).lower() == "true",
                counterparty_id=row.get("counterparty_id", ""),
                counterparty_country=row.get(
                    "counterparty_country",
                    "US"
                ).upper(),
                occurred_at=datetime.now(),
                balance_after=Decimal(row["balance_after"])
                if row.get("balance_after")
                else None,
            )

            db.add(txn)
            count += 1

        db.commit()
        db.close()

        print(f"IMPORTED {count} TRANSACTIONS")

    except Exception as e:
        print("CSV IMPORT ERROR:", e)

    return redirect(url_for("home"))


@app.route("/run-scan", methods=["POST"])
def run_scan():
    if not require_login():
        return redirect(url_for("home"))

    try:
        subprocess.run(
            [sys.executable, "aml_monitor.py"],
            timeout=60,
        )
    except Exception as e:
        print("SCAN ERROR:", e)

    return redirect(url_for("home"))


@app.route("/run-agent", methods=["POST"])
def run_agent():
    if not require_login():
        return redirect(url_for("home"))

    try:
        subprocess.run(
            [sys.executable, "ai_agent.py"],
            timeout=60,
        )
    except Exception as e:
        print("AGENT ERROR:", e)

    return redirect(url_for("home"))


@app.route("/update-alert/<int:alert_id>", methods=["POST"])
def update_alert(alert_id):
    if not require_login():
        return redirect(url_for("home"))

    db = SessionLocal()

    alert = (
        db.query(AMLAlert)
        .filter(AMLAlert.id == alert_id)
        .first()
    )

    if alert:
        alert.status = request.form["status"]
        db.commit()

    db.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
```

    
