# AI-KnowledgeNest

Minimal notes and instructions to deploy this Flask backend to Render (https://render.com).

## What you need
- A Git repository (this project) pushed to GitHub/GitLab (Render connects to a git provider).
- Environment variables configured in Render (see below).

## Required environment variables
Set these in Render's service settings (Environment) or in a local `.env` file for testing.

- `MONGO_URI` — your MongoDB connection string
- `PERPLEXITY_API_KEY` — API key for Perplexity calls
- `FLASK_SECRET_KEY` — Flask session secret
- `FLASK_DEBUG` — `True` or `False` (optional; default `False`)

## How Render will run the service
1. Create a new Web Service on Render.
2. Connect your repository and select the `main` branch.
3. For the **Build Command**, leave blank or use the default (Render will install from `requirements.txt`).
4. For the **Start Command**, set:

```
gunicorn app:app
```

Alternatively, providing a `Procfile` with `web: gunicorn app:app` is supported (already included).

## Local testing
1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill values, then run locally:

```powershell
$env:FLASK_DEBUG = 'True'
python app.py
```

Note: In production (Render), the app is served with Gunicorn which listens on the port provided by Render.

## Notes and next steps
- If you want pinned versions for reproducible builds, I can detect installed versions or suggest stable pins and update `requirements.txt`.
- Add health checks or a `render.yaml` for more advanced Render setup if needed.
