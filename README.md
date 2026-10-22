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

The Django settings module loads `.env` values for local development, while already-defined process environment variables take precedence. The configured VS Code debugger also reads `.env` for you.

New users can register with email and password or Google sign-in. Password-reset messages use a readable console email backend by default and are printed in the server terminal during local development; it decodes wrapped text so reset links can be copied intact. For a real deployment, set `DJANGO_EMAIL_BACKEND` to an appropriate Django email backend and configure its required credentials/settings so reset messages reach users.

### 3. Set up the database

```powershell
python manage.py migrate
```

### 4. Run and debug in VS Code

1. Open this repository folder in VS Code.
2. Select the `venv` Python interpreter if VS Code asks.
3. Open **Run and Debug** and choose **Django: UBCT**.
4. Press **F5**. The debugger loads `.env` and starts the development server at `http://127.0.0.1:8000/`. The debugger disables Django's auto-reloader so breakpoints stay attached to the process serving requests. Stop and restart the debug session after changing code or settings; this server does not reload changes automatically.

The same configuration can be launched from the Run menu. You do not need to generate a new secret every time; keep the generated value in your local ignored `.env` file.
When `DJANGO_DEBUG=true`, failed social sign-ins also log a safe diagnostic category and exception type in the server terminal. Do not share OAuth callback URLs; they contain one-time authorization codes.

### Run from a terminal instead

The Django settings module loads the root `.env` file automatically, so you can start the server with:

```powershell
python manage.py runserver
```

If you need to override a setting for one PowerShell session, set that variable before running the command. Keep using the same local `DJANGO_SECRET_KEY`; do not generate a new one for every server start.

## Uploaded files

New uploads are stored under `media/`, configured by `MEDIA_ROOT` and `MEDIA_URL`. The older `request_documents/`, `fund_transfer_documents/`, and `kyc_docs/` folders may contain files created before media storage was configured. They are ignored by Git along with the new media folder.

Request and transfer document downloads must use the application’s permission-checked download views. Do not expose the media directory or its storage bucket publicly; doing so can bypass application authorization.
