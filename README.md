# Resume Analyzer — Flask

A full-stack resume analyzer built with Python (Flask) backend and a clean HTML/JS frontend. No external APIs needed.

## Project structure

```
resume-analyzer-flask/
├── app.py              # Flask backend — all analysis logic lives here
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend (HTML + CSS + JS)
└── README.md
```

## Run locally

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the server
```bash
python app.py
```

### 3. Open in browser
Go to `http://localhost:5000`

---

## Deploy free on Render

1. Push this project to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Set:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
5. Add `gunicorn` to requirements.txt before deploying
6. Click Deploy — you get a permanent free URL

---

## How it works

- `POST /analyze` — receives resume + job description as JSON, returns analysis as JSON
- Frontend calls this endpoint via `fetch()` and renders the results
- All keyword matching logic is in `app.py` — no external APIs


