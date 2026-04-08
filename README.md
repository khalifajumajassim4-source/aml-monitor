# AML Monitor

A Flask-based AML monitoring demo with a dashboard, CSV upload, rule-based alerts, and Render deployment support.

## Files
- `app.py` - website
- `aml_monitor.py` - scanner
- `aml_rules.py` - rules
- `db.py` - database models
- `requirements.txt` - packages
- `render.yaml` - Render config
- `.env.example` - sample environment values
- `sample_transactions.csv` - test upload file

## Local run
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

## Demo login
- admin
- admin123

## Render
1. Upload all files in this folder to a GitHub repo.
2. In Render, create a Web Service from the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add env vars:
   - `DATABASE_URL=sqlite:///test.db`
   - `SECRET_KEY=some-random-secret`
   - SMTP settings if you want email
