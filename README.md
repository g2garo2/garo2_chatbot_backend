# Garo2 Backend

FastAPI backend for the Garo2 AI chatbot. It supports Google login, JWT auth, MySQL persistence, image uploads, OpenRouter chat completions, and Hostinger VPS deployment.

## 1. Requirements

- Python 3.11+
- MySQL 8+
- A Google OAuth Web Client ID
- An OpenRouter API key

## 2. Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with your real values.

## 3. Database

Create the database first:

```sql
CREATE DATABASE garo2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Run migrations:

```bash
alembic upgrade head
```

## 4. Run locally

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
GET http://127.0.0.1:8000/api/health
GET http://127.0.0.1:8000/
```

## 5. API endpoints

- `POST /api/auth/google`
- `GET /api/auth/me`
- `POST /api/chat/new`
- `GET /api/chat/history`
- `GET /api/chat/{chat_id}`
- `POST /api/chat/{chat_id}/message`
- `DELETE /api/chat/{chat_id}`
- `POST /api/upload/image`
- `GET /api/health`
- `GET /admin`
- `GET /api/admin`
- `GET /api/admin/dashboard`
- `GET /api/admin/default-prompt`
- `PUT /api/admin/default-prompt`
- `GET /api/admin/exports/{dataset}`

## 5A. Admin dashboard

- Open `http://127.0.0.1:8000/admin`
- In production behind the same `/api` proxy, open `https://your-domain/api/admin`
- Sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `backend/.env`
- The admin page shows website metrics, recent users/chats, plan and language breakdowns
- CSV exports are available for `users`, `chats`, `messages`, `payments`, `usage-daily`, and `usage-monthly`
- The default prompt editor updates the backend chat prompt that is appended to Garo2's built-in language rules

## 6. Hostinger VPS deployment

Install Python on the VPS, then:

```bash
cd /var/www/garo2_backend
python3 -m venv venv
source venv/bin/activate
cd /var/www/garo2_backend/garo2_chatbot_backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
gunicorn -k uvicorn.workers.UvicornWorker -w 3 -b 127.0.0.1:8000 app.main:app
```

Use the sample files in `deploy/` for `systemd` and Nginx.

Frontend production env:

```env
VITE_API_BASE_URL=https://amptebmarak.blog/api
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
VITE_RAZORPAY_KEY_ID=your-razorpay-key-id
```

Frontend local dev override:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
VITE_RAZORPAY_KEY_ID=your-razorpay-key-id
```

## 7. Notes

- Keep `OPENROUTER_API_KEY` only in backend `.env`.
- Change the default `ADMIN_USERNAME` and `ADMIN_PASSWORD` before production use.
- Set `CORS_ORIGINS` to your frontend domains.
- Uploaded images are served from `/uploads`.
- If the frontend reports `User not found`, clear the stale `garo2_token` in browser local storage and sign in again.
