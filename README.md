# FinVerse — Personal Finance Management Platform

> **FastAPI · Role-Based Access Control · REST API · Docker · AWS · SQLAlchemy**

A full-stack financial management platform built as a backend engineering project — focused on real authorization, clean API design, and production-grade architecture. Every route is server-enforced. Every decision is documented.

🔗 **[Live Demo](https://your-live-url.aws.com)** — no password required, select a role to explore

---

## ⚡ Quick Start

```bash
git clone https://github.com/your-username/finverse.git
cd finverse
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **http://localhost:8000** — select a role and start exploring.

API docs with every endpoint testable: **http://localhost:8000/docs**

---

## 📸 Screenshots

### Role Selection — Login Page
<!-- Add screenshot: screenshots/login.png -->
> *Screenshot coming soon*

### Dashboard — Admin View
<!-- Add screenshot: screenshots/dashboard-admin.png -->
> *Screenshot coming soon*

### Dashboard — Analyst View
<!-- Add screenshot: screenshots/dashboard-analyst.png -->
> *Screenshot coming soon*

### Swagger API Docs
<!-- Add screenshot: screenshots/swagger.png -->
> *Screenshot coming soon*

---

## 🎯 Why This Project Exists

Most personal finance tools are either too simple (a spreadsheet) or too heavy (a SaaS product with 40 features you don't need). FinVerse is intentionally in the middle — clean, fast, and focused.

The core engineering problem it solves: **how do you build a system where authorization is real, not decorative?**

- Authorization is enforced at the **server level**, not just hidden in the UI
- The API and browser UI share a **single enforcement layer** — no divergence possible
- Data validation happens **before** any database call is made
- Both surfaces are protected by the **same two functions**

## 🧾 At a Glance

- Backend-focused full-stack finance platform
- Role-Based Access Control (admin / analyst / viewer)
- Dual interface: Browser UI + REST API
- Server-side authorization enforcement
- CSV import/export with fault tolerance
- Fully containerized with Docker

This is not a CRUD tutorial project. It is a focused exploration of how access control, API design, and clean architecture interact in a real system.

---

## 🔐 Role-Based Access Control

Three roles. One enforcement layer. No workarounds.

| Role | Access Level |
|---|---|
| `admin` | Full access — create, edit, delete, import, export, analytics |
| `analyst` | Read + analytics + export — no write access |
| `viewer` | Read only — transactions and summary |

### How Enforcement Actually Works

The UI hides buttons based on role — that is cosmetic. The actual protection is two Python functions, called server-side, before any database query runs. Bypassing the UI with Postman or curl changes nothing.

**`get_role(request)`** — base guard, called on every route

```python
def get_role(request: Request) -> str:
    role = request.session.get("role")
    if not role:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=403, detail="Invalid role")
    return role
```

**`require_admin(request)`** — write guard, called on every mutation

```python
def require_admin(request: Request) -> str:
    role = get_role(request)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return role
```

### What a Bypass Attempt Looks Like

An analyst sending `POST /api/transactions` directly — bypassing the UI entirely — receives:

```json
HTTP 403 Forbidden
{ "detail": "Admin access required" }
```

### Permission Matrix

| Action | admin | analyst | viewer |
|---|:---:|:---:|:---:|
| View dashboard | ✅ | ✅ | ✅ |
| View transactions | ✅ | ✅ | ✅ |
| Search, filter, sort | ✅ | ✅ | ❌ |
| Category breakdown | ✅ | ✅ | ❌ |
| Monthly summary | ✅ | ✅ | ❌ |
| Export CSV | ✅ | ✅ | ❌ |
| Add transaction | ✅ | ❌ | ❌ |
| Edit transaction | ✅ | ❌ | ❌ |
| Delete transaction | ✅ | ❌ | ❌ |
| Import CSV | ✅ | ❌ | ❌ |
| REST API reads | ✅ | ✅ | ✅ |
| REST API writes | ✅ | ❌ | ❌ |

---

## 🏗️ Architecture and Design Decisions

### Two Surfaces, One Enforcement Layer

FinVerse exposes two completely separate interfaces for the same operations:

**UI Routes** — HTML form `POST`, `303 See Other` redirect after every action, designed for the browser. Prefixed `/transactions/*` and `/dashboard`.

**REST API Routes** — JSON in and out, proper HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`), designed for Postman, Swagger, or external integration. Prefixed `/api/transactions/*` and `/api/summary/*`.

Both surfaces call the same `get_role()` and `require_admin()` functions. One change to the enforcement layer applies to everything.

### Route Registration Order Is Not Arbitrary

FastAPI matches routes in the order they are registered. `/api/transactions/export` and `/api/transactions/import` must be registered **before** `/api/transactions/{transaction_id}`.

If the parameterized route is registered first, FastAPI attempts to parse `"export"` as an integer transaction ID, fails, and returns `422 Unprocessable Entity` before the handler is ever reached. This behavior highlights how route matching works in FastAPI and why route ordering must be handled carefully in production systems.

### No Frontend Framework — On Purpose

The dashboard is plain HTML with Tailwind CSS, server-rendered via Jinja2. No React, no Vue, no build step. This was deliberate — the backend is the focus. Server-rendered HTML works without JavaScript, on slow connections, and in accessibility tools without extra configuration. Jinja2 conditionals handle role-based UI differences cleanly: `{% if role == "admin" %}`.

### Graceful CSV Import

Bad rows during import are skipped and counted, not thrown as exceptions. The entire batch never fails because of one malformed row.

```python
for row in reader:
    try:
        # parse, validate, create transaction
        imported += 1
    except Exception:
        skipped += 1
        continue
```

The response always reports: `imported: 198, skipped: 2`. This is how production bulk import systems behave.

### Why Explicit Function Calls, Not a Decorator

A decorator-based permission system or middleware layer were both considered. Explicit calls were chosen because the access requirement is visible at the route level — the first line of any handler tells you exactly what access it requires, without needing to check a decorator registry or middleware config.

### SQLite Now, PostgreSQL Ready

The ORM layer (SQLAlchemy) abstracts the database entirely. Swapping from SQLite to PostgreSQL is a single line change in `database.py` — the connection string. No queries, no models, no route logic changes. This is the value of using an ORM correctly.

---

## ✨ Features

### Dashboard (Browser Interface)

- **Summary cards** — total income, total expense, and live balance on every page load
- **Category breakdown** — spending totals grouped by category (analyst + admin)
- **Monthly summary** — totals grouped by month in `YYYY-MM` format (analyst + admin)
- **Full-text search** — across both category name and transaction notes simultaneously
- **Filters** — by type, category partial match, and date range, all combinable
- **Sorting** — by date or amount, ascending or descending
- **Pagination** — page-by-page navigation with all active filters preserved
- **Inline row editing** — fields become editable in place, highlighted in yellow while active
- **Delete with confirmation** — browser prompt before any delete
- **CSV export** — one click, file downloads immediately
- **CSV bulk import** — valid rows imported, bad rows skipped and counted, batch never crashes
- **Role badges** — active role displayed in the header on every page

### REST API

- Full CRUD via proper HTTP verbs
- Same filtering, sorting, and pagination available as query parameters
- Analytics endpoints: summary totals, category breakdown, monthly breakdown
- CSV export and import via API with JSON response
- All 17 endpoints documented and testable at `/docs`

---

## 📡 REST API Reference

All routes require an active session. Log in via the browser or include the session cookie in your requests. Full interactive Swagger UI available at `/docs`.

### Authentication

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/` | Public | Renders the login page |
| `POST` | `/login` | Public | Sets session role. Form field: `role` |
| `GET` | `/logout` | Any role | Clears session, redirects to login |

```bash
# Login via curl
curl -X POST http://localhost:8000/login \
  -d "role=admin" \
  -c cookies.txt
```

### Transactions

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/api/transactions` | Any role | Paginated list with optional filters |
| `POST` | `/api/transactions` | Admin only | Create a new transaction |
| `GET` | `/api/transactions/{id}` | Any role | Get one transaction by ID |
| `PUT` | `/api/transactions/{id}` | Admin only | Fully update a transaction |
| `DELETE` | `/api/transactions/{id}` | Admin only | Delete a transaction |
| `GET` | `/api/transactions/export` | Analyst + Admin | Download all as CSV |
| `POST` | `/api/transactions/import` | Admin only | Bulk import from CSV |

### Query Parameters — `GET /api/transactions`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `type` | string | — | `income` or `expense` |
| `category` | string | — | Partial match, case-insensitive |
| `start_date` | string | — | Format: `YYYY-MM-DD` |
| `end_date` | string | — | Format: `YYYY-MM-DD` |
| `search` | string | — | Searches category and notes simultaneously |
| `sort` | string | `date_desc` | `date_desc` `date_asc` `amount_desc` `amount_asc` |
| `page` | integer | `1` | Page number |
| `limit` | integer | `10` | Results per page, max 100 |

```
GET /api/transactions?type=expense&search=rent&sort=amount_desc&page=1&limit=5
```

### Request / Response Examples

```json
// POST /api/transactions
{
  "amount": 1500.00,
  "type": "expense",
  "category": "Utilities",
  "date": "2025-04-01",
  "notes": "Electricity bill for April"
}

// 201 Created
{ "message": "Transaction created", "id": 42 }
```

```json
// GET /api/summary
{
  "total_income": 85000.00,
  "total_expense": 42300.00,
  "balance": 42700.00
}
```

```json
// GET /api/summary/category
[
  { "category": "Salary",    "total": 85000.00 },
  { "category": "Rent",      "total": 18000.00 },
  { "category": "Groceries", "total": 6200.00  }
]
```

```json
// POST /api/transactions/import
{ "message": "Import complete", "imported": 198, "skipped": 2 }
```

### Analytics Endpoints

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/api/summary` | Any role | Total income, expense, balance |
| `GET` | `/api/summary/category` | Analyst + Admin | Totals by category |
| `GET` | `/api/summary/monthly` | Analyst + Admin | Totals by month |
| `GET` | `/api/summary/recent` | Any role | 10 most recent transactions |

---

## ✅ Data Validation

Every write operation — whether from the browser form or the REST API — goes through Pydantic validation before any database call.

```python
class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)       # must be a positive number
    type: str                         # must be "income" or "expense"
    category: str                     # required string
    date: date                        # must parse as a valid date
    notes: str = ""                   # optional, defaults to empty

    @validator("type")
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be income or expense")
        return v
```

Invalid input returns `422 Unprocessable Entity` with field-level detail before the route function runs. Form-based routes apply the same checks manually for consistent behaviour across both surfaces.

### CSV Import Format

Column names are case-sensitive. Notes column is optional.

```
Amount,Type,Category,Date,Notes
85000,income,Salary,2025-04-01,April salary
18000,expense,Rent,2025-04-02,Monthly rent
1200,expense,Groceries,2025-04-03,Weekly groceries
```

Rows with unrecognized type, non-positive amount, missing required columns, or malformed dates are silently skipped. The import never rolls back due to a single bad row.

---

## 🧪 Testing

```bash
pytest -v
```

The test suite covers:

- RBAC enforcement paths (the most critical — a regression here is a security issue, not just a bug)
- Full transaction CRUD lifecycle
- Validation edge cases: negative amounts, missing fields, invalid types
- Dashboard route and analytics API

---

## 🚀 Deployment

FinVerse is deployed on **AWS** using Docker and served via Uvicorn.

- Containerized with Docker for a consistent, reproducible environment
- Served via Uvicorn (ASGI, production-grade)
- SQLite for demo deployment — PostgreSQL-ready with a single config change
- Session management via signed itsdangerous cookies

**Live:** [your-live-url.aws.com](https://your-live-url.aws.com)

### Running with Docker

```bash
# Build
docker build -t finverse .

# Run
docker run -p 8000:8000 finverse
```

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential sqlite3 libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ⚙️ Configuration

No environment variables are required for local setup.

For production deployments:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (defaults to SQLite) |
| `SECRET_KEY` | Session signing key — must be set securely in production |

---

## 🛠️ Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend | FastAPI (Python 3.12) | Async-ready, automatic Swagger UI, type-safe routing |
| ORM | SQLAlchemy 2.0 | Composable queries, database-agnostic |
| Database | SQLite → PostgreSQL | Zero setup locally; one-line swap for production |
| Validation | Pydantic v2 | Strict input validation before any DB write |
| Templating | Jinja2 | Server-rendered HTML, no JavaScript required |
| Sessions | Starlette + itsdangerous | Signed, tamper-proof session cookies |
| Styling | Tailwind CSS (CDN) | Fast, utility-first, no build step |
| Server | Uvicorn (ASGI) | Production-grade async server |
| Containers | Docker | Consistent environment, AWS-ready |
| Migrations | Alembic | Schema versioning for production DB changes |

---

## 📁 Project Structure

```
finverse/
├── app/
│   ├── main.py                   # App entry point, middleware, router registration
│   ├── db/
│   │   └── database.py           # SQLAlchemy engine, session factory, get_db dependency
│   ├── models/
│   │   └── transaction.py        # Transaction ORM model
│   ├── api/
│   │   ├── deps.py               # Shared FastAPI dependencies
│   │   └── routes/
│   │       └── transactions.py   # All routes: auth, dashboard, UI forms, REST API
│   └── templates/
│       ├── login.html            # Role selection login page
│       └── dashboard.html        # Main dashboard — analytics, table, forms
├── tests/
│   └── test_transactions.py      # RBAC, CRUD, and validation tests
├── screenshots/                  # UI screenshots for README
├── Dockerfile
├── requirements.txt
├── finance.db
└── README.md
```

**`transactions.py`** is organized in this order:

1. Constants — `VALID_ROLES`, `VALID_TYPES`
2. Pydantic schemas — `TransactionCreate`, `TransactionUpdate`
3. RBAC helpers — `get_role`, `require_admin`
4. Analytics helpers — `calculate_summary`, `apply_filters`, `apply_sorting`
5. Auth routes — `/`, `/login`, `/logout`
6. Dashboard route — `/dashboard`
7. UI form routes — `/transactions/*`
8. REST API routes — `/api/transactions/*`, `/api/summary/*`

---

## 📦 Notes

The following are excluded from version control:

```
venv/
__pycache__/
*.pyc
finance.db
.env
```

---

## 🔭 What I Would Build Next

These are the concrete next steps to make this production-ready:

**JWT Authentication** — Replace the demo role-select login with proper JWT tokens, bcrypt password hashing, a users table, and token expiry. The session mechanism is production-grade; the login itself is a demo shortcut.

**Alembic Migrations** — The dependency is already in `requirements.txt`. The next step is initializing migration scripts so schema changes can be applied to a live database without dropping tables.

**Test Coverage Expansion** — Integration tests specifically for the RBAC enforcement paths, plus edge cases around pagination, filter combinations, and CSV import edge cases.

**Chart Visualizations** — The analytics data is already calculated and passed to the template on every dashboard load. Adding Chart.js for monthly and category data is a frontend-only change — no backend work required.

**Rate Limiting** — Per-IP rate limiting on login and import endpoints to prevent abuse on a public deployment.

**PostgreSQL on AWS RDS** — SQLite is fine for a demo. A real multi-user deployment needs Postgres. The SQLAlchemy layer makes this a one-line change in `database.py`.

---

## 👤 Author

**Jay Soni**

Built as a backend engineering assessment focused on role-based access control, REST API design, and full-stack FastAPI architecture.

[GitHub](https://github.com/your-username) · [LinkedIn](https://linkedin.com/in/your-profile) · [Live Demo](https://your-live-url.aws.com)