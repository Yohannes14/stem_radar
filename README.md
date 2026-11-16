# STEM RADAR 📡
### Enterprise AI-Powered STEM & Technology Intelligence Platform

STEM RADAR is a modular intelligence platform supporting both an interactive **Telegram Bot** and a high-performance **FastAPI REST API**, designed to collect, categorize, deduplicate, analyze, rank, and transform high-impact developments across **19 STEM domains**:

*Artificial Intelligence, Machine Learning, Robotics, Computer Science, Software Engineering, Cybersecurity, Electronics, Embedded Systems, Internet of Things, Mechanical Engineering, Electrical Engineering, Biotechnology, Physics, Chemistry, Mathematics, Space Technology, Renewable Energy, STEM Education, and Emerging Technologies.*

---

## 🏛️ Clean Architecture / Modular Monolith

```
stem-radar/
├── app/
│   ├── main.py                  # CLI & Telegram runtime entry point
│   ├── config.py                # Configuration and logging shims
│   │
│   ├── core/                    # Core Infrastructure & Cross-Cutting Concerns
│   │   ├── config.py            # Pydantic Settings (API, Telegram, DB, AI)
│   │   ├── exceptions.py        # Domain-driven Exception hierarchy
│   │   └── logging.py           # Standardized structured logging
│   │
│   ├── database/                # Persistence & Data Access
│   │   ├── models.py            # SQLAlchemy 2.0 ORM models (Article, Category, Watchlist, etc.)
│   │   ├── database.py          # Async engine, connection pooling, SQLite migrations
│   │   └── repository.py        # Asynchronous Repository pattern
│   │
│   ├── collectors/              # Multi-Source Ingestion Pipeline
│   │   ├── base.py              # BaseCollector interface & CollectedArticle schema
│   │   ├── client.py            # Resilient HTTP client with retry & exponential backoff
│   │   ├── rss_collector.py     # High-throughput RSS / Atom parser
│   │   ├── arxiv_collector.py   # Official arXiv API paper ingestor
│   │   └── github_collector.py  # Trending GitHub repository monitor
│   │
│   ├── processors/              # Pure Domain Business Logic
│   │   ├── classifier.py        # 19-domain STEM classifier (tokenization & scoring)
│   │   ├── deduplicator.py      # Tracking param stripping & URL SHA-256 hashing
│   │   └── ranking.py           # Multi-factor intelligence ranking engine (ArticleRanker)
│   │
│   ├── services/                # Shared Application Services (Pure Business Logic)
│   │   ├── news_service.py      # Multi-source ingestion & query service
│   │   ├── content_service.py   # STEM content opportunity generator
│   │   ├── automation_service.py# Briefings, watchlists, quiet hours & scoring
│   │   └── ai/                  # Modular AI Intelligence Engine
│   │       ├── service.py       # Summaries, research analysis, concept explanations
│   │       ├── cache.py         # SHA-256 TTL response cache
│   │       ├── cost_tracker.py  # Token accounting and cost estimation
│   │       └── adapters/        # OpenAI adapter & heuristic fallback engines
│   │
│   ├── bot/                     # Adapter 1: Telegram Presentation Layer
│   │   ├── bot.py               # Bot builder, lifecycle & error handlers
│   │   ├── handlers/            # Handlers (/news, /briefing, /learn, /quiz, /watchlist, etc.)
│   │   ├── keyboards/           # Interactive inline keyboards
│   │   └── ui/                  # Mobile Telegram markdown formatters
│   │
│   └── api/                     # Adapter 2: FastAPI REST API Layer
│       ├── main.py              # FastAPI application factory & async lifespan
│       ├── dependencies.py      # Dependency injection (DB session, auth, services)
│       ├── exceptions.py        # Centralized exception handlers & error envelopes
│       ├── middleware/          # Request logging & in-memory sliding-window rate limiter
│       └── v1/
│           ├── router.py        # V1 aggregation router
│           ├── endpoints/       # Route handlers (health, news, trending, research, categories, ai)
│           └── schemas/         # Pydantic DTOs & response schemas
│
├── bot.py                       # Standalone Telegram Bot launcher
├── api.py                       # Standalone FastAPI server launcher
├── tests/                       # 114 Automated tests (100% mocked, 0 external network dependencies)
├── data/                        # Persistent local SQLite storage
├── Makefile                     # Developer productivity shortcuts
├── requirements.txt             # Pinned project dependencies
└── pyproject.toml               # Build, pytest, and ruff configuration
```

---

## ⚡ Developer Commands (Makefile)

| Command | Action |
| :--- | :--- |
| `make install` | Install dependencies into virtual environment |
| `make run` | Start the Telegram Bot |
| `make run-api` | Start the FastAPI REST Server (`http://127.0.0.1:8000`) |
| `make collect` | Run a one-shot multi-source intelligence collection |
| `make init-db` | Initialize database schema and seed default STEM categories |
| `make test` | Execute the full automated pytest suite |
| `make lint` | Run Ruff static analysis |
| `make format` | Automatically fix and format the codebase with Ruff |
| `make clean` | Clean up cache and temporary files |

---

## 🚀 Getting Started

### 1. Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
```ini
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_token_from_botfather
ALLOWED_TELEGRAM_USER_IDS=your_telegram_id

# Database
DATABASE_URL=sqlite+aiosqlite:///data/stem_radar.db

# FastAPI REST Server & Security
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your_secure_api_key_here
API_RATE_LIMIT_PER_MINUTE=60

# Optional AI Configuration (Falls back to deterministic heuristics if unset)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

### 3. Initialize Database
```bash
make init-db
make collect
```

### 4. Running the Applications
Both applications are **independently runnable** and can run simultaneously on the same database:

- **Run Telegram Bot:**
  ```bash
  make run
  # or: python bot.py
  ```

- **Run FastAPI REST Server:**
  ```bash
  make run-api
  # or: python api.py
  ```

---

## 📖 REST API Documentation

When the FastAPI server is running, interactive OpenAPI documentation is available locally at:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON:** [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)

### Available Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/health` | Application status, version, and DB connectivity | No |
| `GET` | `/api/v1/categories` | Complete registry of the 19 STEM domains | No |
| `GET` | `/api/v1/news` | Paginated articles with category, source, & search query | No |
| `GET` | `/api/v1/news/{article_id}` | Detailed single article record | No |
| `GET` | `/api/v1/trending` | SOTA breakthroughs ranked by composite impact score | No |
| `GET` | `/api/v1/research` | Scientific research papers from arXiv with abstracts | No |
| `POST` | `/api/v1/ai/summarize` | Executive AI technical news summary | **Yes** (API Key) |
| `POST` | `/api/v1/ai/explain` | Multi-tier conceptual breakdown (`beginner`, `intermediate`, `advanced`) | **Yes** (API Key) |

### Authentication
Protected endpoints require an API key passed via:
- Header: `X-API-Key: <your_api_key>`
- Or Header: `Authorization: Bearer <your_api_key>`

If no `API_KEY` is set in development, access is granted with unrestricted dev mode. In production, unauthenticated requests return `401 Unauthorized`.

---

## 🤖 Telegram Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Welcome screen & STEM domain explorer |
| `/help` | Complete command reference catalog |
| `/news` | Latest intelligence across all sources with inline pagination |
| `/briefing` | Personalized daily executive STEM briefing |
| `/trending` | High-impact developments scored by ArticleRanker |
| `/watchlist` | Manage technology watchlists (`add`, `remove`, `clear`) |
| `/settings` | Inline settings panel (notifications, quiet hours, domain filters) |
| `/stats` | Platform telemetry and personal intelligence statistics |
| `/learn` | Multi-tier interactive STEM lesson |
| `/roadmap` | 4-phase structured engineering curriculum |
| `/quiz` | Interactive multiple-choice comprehension test |
| `/compare` | Architectural concept comparison matrix |
| `/project` | Hands-on engineering portfolio project recommendation |
| `/vocabulary` | Domain-specific technical glossary |
| `/progress` | Learning mastery and quiz score history |
| `/research` | Latest arXiv research papers |
| `/github` | Trending open-source repositories |
| `/sources` | Intelligence source health telemetry |
| `/collect` | Trigger instant multi-source collection pass |
| `/search` | Full-text article search |
| `/saved` | View bookmarked articles |

---

## 🧪 Testing & Verification

The test suite runs 100% mocked without external network dependencies:

```bash
# Run pytest test suite
make test

# Run Ruff static analysis
make lint
```
