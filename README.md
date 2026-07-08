# AI-Native ERP

> **Multi-Tenant AI-Native ERP Platform** — monorepo containing the Next.js 14 frontend and FastAPI async backend.

---

## Repository Structure

```
AI NATIVE ERP/
├── frontend/                   # Next.js 14 (App Router) — TypeScript
│   ├── src/
│   │   ├── app/                # Next.js App Router pages & layouts
│   │   ├── components/         # Reusable UI components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # Supabase client, API helpers
│   │   ├── store/              # Zustand global state slices
│   │   ├── types/              # Shared TypeScript interfaces
│   │   └── utils/              # Pure utility functions
│   ├── public/                 # Static assets
│   ├── .env.example            # ← copy to .env.local and fill in
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── package.json
│   ├── .eslintrc.json
│   └── .prettierrc.json
│
├── backend/                    # FastAPI — Python 3.11+
│   ├── app/
│   │   ├── api/                # Route handlers (v1/…)
│   │   ├── core/               # Config, database, security
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic & AI integrations
│   │   └── utils/              # Shared helper functions
│   ├── alembic/                # Database migration scripts
│   ├── tests/                  # Pytest async test suite
│   ├── main.py                 # FastAPI application entry point
│   ├── requirements.txt
│   └── .env.example            # ← copy to .env and fill in
│
├── .gitignore
└── README.md
```

---

## Quick Start

### Prerequisites
| Tool | Version |
|------|---------|
| Node.js | ≥ 20 LTS |
| Python | ≥ 3.11 |
| Supabase CLI | latest |
| Redis | ≥ 7 (for Celery) |

---

### Frontend

```bash
cd frontend
cp .env.example .env.local        # fill in SUPABASE_URL + SUPABASE_ANON_KEY
npm install
npm run dev                        # → http://localhost:3000
```

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate             # Windows
# source .venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
cp .env.example .env               # fill in all <REPLACE_ME> values
uvicorn main:app --reload          # → http://localhost:8000/api/docs
```

---

## Environment Variables

| Variable | Location | Description |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `frontend/.env.local` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `frontend/.env.local` | Supabase public anon key |
| `SUPABASE_URL` | `backend/.env` | Supabase project URL |
| `SUPABASE_ANON_KEY` | `backend/.env` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | `backend/.env` | Supabase service role key (**secret**) |
| `DATABASE_URL` | `backend/.env` | asyncpg Postgres connection string |
| `SECRET_KEY` | `backend/.env` | JWT signing key |
| `OPENAI_API_KEY` | `backend/.env` | OpenAI API key for AI features |

> ⚠️ **Never commit `.env` or `.env.local` files.** They are excluded via `.gitignore`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend Framework | Next.js 14 (App Router) |
| Language | TypeScript 5 |
| State Management | Zustand + TanStack Query |
| Backend Framework | FastAPI 0.111 |
| Database / Auth | Supabase (PostgreSQL + Auth + Storage) |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Task Queue | Celery + Redis |
| AI/LLM | OpenAI, Anthropic, LangChain |
| Logging | structlog |
| Error Tracking | Sentry |
