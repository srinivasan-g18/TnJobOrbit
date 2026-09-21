# TnJobOrbit

TnJobOrbit is a mobile-friendly Tamil Nadu government-job/exam preparation platform.

## Included

- Public homepage
- Government Jobs
- Notes/PDF downloads
- Study materials
- Previous-year papers
- Mock tests with scoring
- Search/filtering
- Local browser bookmarks and test history
- Instagram + WhatsApp links
- One Admin account
- Admin dashboard
- Admin uploads
- Test/question builder
- Categories
- Publish/unpublish
- Explicit Admin deletion
- No automatic content expiration/deletion
- PWA manifest/service worker

## 1. Install

Python 3.10+ recommended.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

## 2. Configure Admin

Copy `.env.example` to `.env` if you use an environment-variable loader, or set environment variables in your terminal/server.

For the included simple setup, you can set:

Windows PowerShell:

```powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="YOUR_STRONG_PASSWORD"
$env:SECRET_KEY="YOUR_LONG_RANDOM_SECRET"
python app.py
```

The first database initialization uses those values.

If you do not set them, the development defaults are:
username `admin`
password `ChangeMe123!`

CHANGE THE PASSWORD immediately from Admin > Change Password.

## 3. Run

```bash
python app.py
```

Open:

http://127.0.0.1:5000

Admin:

http://127.0.0.1:5000/admin/login

## 4. Important production notes

This project is a complete starter application, but for a public production launch you should:

- Use HTTPS.
- Set a strong SECRET_KEY.
- Set a strong admin password.
- Put the database and uploaded files on persistent server storage/backups.
- Use a production WSGI server such as Waitress or Gunicorn.
- Consider PostgreSQL + object storage when usage becomes large.
- Add CSRF protection before public production deployment.
- Add rate limiting and stronger security headers.
- Back up `tnjoborbit.db` and `uploads/`.
- Never commit `.env` or real credentials to Git.

## Content permanence

The application has NO automatic content deletion by date.

Old notes, tests, jobs, papers and materials remain in the database until the Admin explicitly deletes or unpublishes them.

Unpublishing hides content from public users but keeps the database record.

## User model

Public users do not need an account. Their bookmarks and test history are stored in browser localStorage.

If you later want a cloud-based "My Portal" that follows a user across devices, add a separate user authentication system. The current master content model is already separated from user-side browser data.
