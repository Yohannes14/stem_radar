# STEM RADAR 📡
### Enterprise AI-Powered STEM & Technology Intelligence Platform

STEM RADAR is a modular intelligence platform and interactive Telegram bot designed to collect, categorize, deduplicate, analyze, rank, and transform high-impact developments across **19 STEM domains**:

*Artificial Intelligence, Machine Learning, Robotics, Computer Science, Software Engineering, Cybersecurity, Electronics, Embedded Systems, Internet of Things, Mechanical Engineering, Electrical Engineering, Biotechnology, Physics, Chemistry, Mathematics, Space Technology, Renewable Energy, STEM Education, and Emerging Technologies.*

---

## 🏛️ Senior Architecture (Clean Architecture / Hexagonal)

```
stem-radar/
├── app/
│   ├── main.py                  # Single robust CLI & runtime coordinator
│   ├── config.py                # Backwards-compatible configuration shim
│   │
│   ├── core/                    # Core Infrastructure & Cross-Cutting Concerns
│   │   ├── config.py            # Pydantic Settings with strict validation & typing
│   │   ├── exceptions.py        # Domain-driven Exception hierarchy
│   │   └── logging.py           # Standardized structured logging
│   │
│   ├── database/                # Persistence & Data Access
│   │   ├── models.py            # SQLAlchemy 2.0 ORM Mapped models
│   │   ├── database.py          # Async engine, connection pooling, seeders
│   │   └── repository.py        # Asynchronous Repository pattern
│   │
│   ├── collectors/              # Ingestion Strategy Adapters
│   │   ├── base.py              # BaseCollector interface & CollectedArticle schema
│   │   ├── client.py            # Resilient HTTP client with retry & exponential backoff
│   │   ├── registry.py          # Centralized dynamic Source Registry
│   │   ├── rss_collector.py     # High-throughput RSS / Atom parser
│   │   ├── arxiv_collector.py   # Official arXiv API paper ingestor
│   │   ├── github_collector.py  # Trending GitHub repository monitor
│   │   ├── x_collector.py       # Official X API collector (disabled gracefully)
│   │   └── linkedin_collector.py# Official LinkedIn API collector (disabled gracefully)
│   │
│   ├── processors/              # Pure Domain Business Logic
│   │   ├── classifier.py        # 19-domain STEM classifier (tokenization & scoring)
│   │   ├── deduplicator.py      # Tracking param stripping & URL SHA-256 hashing
│   │   └── ranking.py           # Multi-factor intelligence ranking engine
│   │
│   ├── services/                # Application Services
│   │   ├── news_service.py      # Core News Ingestion & Query service
│   │   ├── content_service.py   # STEM Content Opportunity Finder (LinkedIn, Carousels, Video Scripts)
│   │   └── ai_service.py        # Dedicated AI service layer
│   │
│   └── bot/                     # Telegram Presentation Layer
│       ├── bot.py               # Bot builder, lifecycle & error handlers
│       ├── filters/             # User ID whitelist security filter
│       ├── keyboards/           # Interactive inline keyboards
│       ├── ui/                  # Presentation formatters & message chunking
│       └── handlers/            # Handlers (/news, /ideas, /trending, /digest, etc.)
│
├── tests/                       # 24 Automated unit & integration tests (100% mocked)
├── data/                        # Local SQLite persistent storage
├── Makefile                     # Developer productivity shortcuts
├── requirements.txt             # Pinned project dependencies
└── pyproject.toml               # Modern build, pytest & ruff configuration
```

---

## ⚡ Developer Commands (Makefile)

The project includes a developer `Makefile` for one-command workflows:

| Command | Action |
| :--- | :--- |
| `make run` | Start the Telegram Bot |
| `make collect` | Run a one-shot multi-source intelligence collection |
| `make init-db` | Initialize database schema and seed default STEM categories |
| `make test` | Run the full automated test suite with pytest |
| `make lint` | Run Ruff static analysis |
| `make format` | Automatically fix and format the codebase with Ruff |

---

## 🚀 Getting Started (Step-by-Step for macOS)

### 1. Activate Environment
```bash
source .venv/bin/activate
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` if not already present:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```ini
TELEGRAM_BOT_TOKEN=your_token_from_botfather
ALLOWED_TELEGRAM_USER_IDS=your_telegram_id
DATABASE_URL=sqlite+aiosqlite:///data/stem_radar.db
LOG_LEVEL=INFO

# Optional: Proxy if api.telegram.org is restricted in your region/network
# TELEGRAM_PROXY_URL=http://127.0.0.1:7890
```

### 3. Initialize Database & Collect Initial Feeds
```bash
make init-db
make collect
```

### 4. Start the Bot
```bash
make run
```
*(Or `python bot.py`)*

---

## 🤖 Bot Commands Catalog

| Command | Description |
| :--- | :--- |
| `/start` | Welcome message and interactive STEM domain explorer |
| `/help` | Detailed command reference |
| `/news` | Latest intelligence across all sources with pagination |
| `/trending` | High-impact developments scored by the ranking engine |
| `/ideas` | **Content Opportunity Finder:** Transforms tech news into LinkedIn posts, 5-slide carousels, video scripts, and vocabulary |
| `/digest` | Daily intelligence brief |
| `/ai` | Artificial Intelligence & Machine Learning developments |
| `/robotics` | Humanoids, autonomous systems & drones |
| `/science` | Physics, chemistry & biotechnology breakthroughs |
| `/engineering` | Electronics, chips & embedded systems |
| `/programming` | Software engineering, compilers & computer science |
| `/research` | Latest research papers from arXiv |
| `/github` | Trending open-source repositories |
| `/sources` | List all active intelligence feeds |
| `/collect` | Trigger instant multi-source intelligence collection |
| `/search <query>` | Search collected articles by keyword |
| `/saved` | View bookmarked articles |
| `/settings` | Configure notification alerts & preferred categories |

---

## 🧪 Testing & Code Quality

Run tests:
```bash
make test
```
Run linter:
```bash
make lint
```
