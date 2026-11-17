# Deploy KORVA to Vercel (demo mode)
1. `npm i -g vercel && vercel login`
2. In this folder: `vercel link`  (accept defaults)
3. Add env vars (Production):
   ```
   vercel env add SECRET_KEY production        # any long random string
   vercel env add ADMIN_EMAIL production
   vercel env add ADMIN_PASSWORD production
   vercel env add AUTO_SEED production         # value: 1
   vercel env add FLASK_ENV production         # value: production
   ```
4. `vercel --prod`  → prints your live URL.

Demo mode uses SQLite in /tmp: the catalogue is re-seeded on cold start, and carts/orders/accounts
are NOT durable. For a real store, set DATABASE_URL to a hosted PostgreSQL (Neon / Vercel Postgres).
