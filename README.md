# ESSENCE PREMIER — E-Business Platform

FastAPI + Supabase backend and HTML/JS frontend for the ESSENCE PREMIER medical procurement platform.
Implements all five e-business modules required for the course final project.

---

## E-Business Modules Covered

| Module | Pages / Endpoints |
|--------|-------------------|
| Web Selling | `index.html`, `catalog.html`, `cart.html`, `checkout.html` |
| CRM | `crm.html`, `/api/v1/crm/*` |
| Finance Management | `finance.html`, `/api/v1/finance/*` |
| Ordering System | `checkout.html`, `dashboard.html`, `/api/v1/orders/*`, `/api/v1/products/*` |
| Supply Chain Management | `supply_chain.html`, `/api/v1/supply-chain/*` |

---

## Project Structure

```
essence-premier-backend/
├── main.py                          # FastAPI app entry point (v2.0)
├── config.py                        # Settings (reads .env)
├── dependencies.py                  # JWT auth dependency
├── requirements.txt
├── .env.example
│
├── routers/
│   ├── auth.py                      # /auth
│   ├── products.py                  # /products
│   ├── cart.py                      # /cart
│   ├── orders.py                    # /orders
│   ├── crm.py                       # /crm
│   ├── finance.py                   # /finance
│   └── supply_chain.py              # /supply-chain
│
├── migrations/
│   ├── 001_initial_schema.sql       # Core tables
│   └── 002_crm_finance_supply_chain.sql  # CRM, Finance, Supply Chain tables
│
└── frontend/
    ├── api.js                       # Shared API client
    ├── index.html                   # Landing page
    ├── login.html                   # Auth
    ├── catalog.html                 # Product catalog
    ├── cart.html                    # Cart
    ├── checkout.html                # Checkout
    ├── dashboard.html               # User dashboard
    ├── crm.html                     # CRM module
    ├── finance.html                 # Finance module
    ├── supply_chain.html            # Supply chain module
    └── about.html
```

---

## Quick Start

### 1. Supabase Setup

1. Go to supabase.com and create a project.
2. In the SQL Editor, run both files in order:
   - `migrations/001_initial_schema.sql`
   - `migrations/002_crm_finance_supply_chain.sql`
3. Copy your URL, anon key, and service role key from Settings > API.

### 2. Environment

```bash
cp .env.example .env
```

Fill in:
```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
APP_SECRET_KEY=any-random-string
ALLOWED_ORIGINS=http://127.0.0.1:5500
```

### 3. Run Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs

### 4. Serve Frontend

```bash
cd frontend
python -m http.server 5500
```

Open http://127.0.0.1:5500

---

## API Summary

All endpoints prefixed `/api/v1`.

### Auth: `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me`
### Products: `GET /products`, `GET /products/{id}`
### Cart: `GET/POST/PATCH/DELETE /cart` and `/cart/items`
### Orders: `POST/GET /orders`, `PATCH /orders/{id}/cancel`
### CRM: `GET/POST /crm/contacts`, interactions, summary
### Finance: `GET/POST /finance/invoices`, revenue, summary
### Supply Chain: suppliers, purchase-orders, partners

---

## Deployment

**Backend** — Railway, Render, or Fly.io:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Frontend** — Netlify or Vercel (drag and drop the `frontend/` folder).

Update `API_BASE` in `frontend/api.js` to your deployed backend URL before deploying the frontend.
