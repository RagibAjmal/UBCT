# United Brothers Charitable Trust Portal

Django application for the United Brothers Charitable Trust request and fund-transfer workflows.

## Local development on Windows

### 1. Create and activate a virtual environment

From the repository root in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use the virtual environment interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Create your local environment file

Copy the example file and generate a local Django secret once:

```powershell
Copy-Item .env.example .env
python -c "from pathlib import Path; import secrets; p=Path('.env'); p.write_text(p.read_text().replace('DJANGO_SECRET_KEY=', 'DJANGO_SECRET_KEY='+secrets.token_urlsafe(50), 1))"
```

The `.env` file is ignored by Git. Do not commit it or share its secret key. `DJANGO_DEBUG` can be set to `true` for local development. Google sign-in requires `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`; those values are optional for running the application without Google OAuth. To enable Google sign-in, add your OAuth client ID and secret from Google Cloud Console to the matching entries in `.env`.

The Django settings module reads environment variables; Django does not load `.env` itself. The configured VS Code debugger reads `.env` for you.

### 3. Set up the database

```powershell
python manage.py migrate
```

### 4. Run and debug in VS Code

1. Open this repository folder in VS Code.
2. Select the `venv` Python interpreter if VS Code asks.
3. Open **Run and Debug** and choose **Django: UBCT**.
4. Press **F5**. The debugger loads `.env` and starts the development server at `http://127.0.0.1:8000/`. The debugger disables Django's auto-reloader so breakpoints stay attached to the process serving requests.

The same configuration can be launched from the Run menu. You do not need to generate a new secret every time; keep the generated value in your local ignored `.env` file.

### Run from a terminal instead

For a terminal-only run, environment variables need to be loaded into that PowerShell session. One simple approach is to set them for the session:

```powershell
$env:DJANGO_SECRET_KEY = "paste-your-local-secret-here"
$env:DJANGO_DEBUG = "true"
python manage.py runserver
```

Use the same local development secret for subsequent terminal sessions rather than generating a different one each time. These variables are not automatically loaded from `.env` by `python manage.py runserver`.

## Uploaded files

New uploads are stored under `media/`, configured by `MEDIA_ROOT` and `MEDIA_URL`. The older `request_documents/`, `fund_transfer_documents/`, and `kyc_docs/` folders may contain files created before media storage was configured. They are ignored by Git along with the new media folder.

Request and transfer document downloads must use the application’s permission-checked download views. Do not expose the media directory or its storage bucket publicly; doing so can bypass application authorization.
