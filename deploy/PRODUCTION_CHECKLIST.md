# Garo2 V9 Production Checklist

## Backend

1. Copy `backend/.env.example` to the server as `.env`.
2. Set real values for:
   - `SECRET_KEY`
   - `ADMIN_PASSWORD`
   - MySQL credentials
   - `GOOGLE_CLIENT_ID`
   - `OPENROUTER_API_KEY`
   - `GEMINI_API_KEY`
   - `RAZORPAY_KEY_ID`
   - `RAZORPAY_KEY_SECRET`
   - `RAZORPAY_PLAN_PLUS`
   - `RAZORPAY_PLAN_PRO`
   - `RAZORPAY_PLAN_ULTRA`
   - `RAZORPAY_WEBHOOK_SECRET`
   - `BACKEND_BASE_URL=https://amptebmarak.blog`
   - `CORS_ORIGINS=https://garo2.com,https://www.garo2.com,https://admin.garo2.com`
3. Keep `APP_ENV=production`.
4. Keep `APP_DEBUG=false`.
5. Run `alembic upgrade head`.
6. Restart `garo2-backend`.
7. Verify `GET /api/health`.

## Frontend

1. Set:
   - `VITE_API_BASE_URL=https://amptebmarak.blog/api`
   - `VITE_GOOGLE_CLIENT_ID=...`
   - `VITE_RAZORPAY_KEY_ID=...`
2. Run `npm install`.
3. Run `npm run build`.
4. Deploy the contents of `frontend/dist`.
5. Include `frontend/public/.htaccess` in the deployed static files if the host uses Apache or LiteSpeed.

## Verify before go-live

1. Google login works from the real frontend domain.
2. `/api/admin` prompts for Basic Auth and loads after valid credentials.
3. `/pricing` loads plans from `GET /api/plans`.
4. Paid checkout opens Razorpay using the public key only.
5. Webhook endpoint is configured with the same `RAZORPAY_WEBHOOK_SECRET`.
6. Uploaded image URLs resolve from the public backend domain.
